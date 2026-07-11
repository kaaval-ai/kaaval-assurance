import sqlite3
import tempfile
import json
import os
from kaaval_assurance.compare_runs import load_db_metrics, compare_runs, CAVEATS

def create_mock_db(db_path: str, rows: list):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE trajectory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id TEXT NOT NULL,
            tier TEXT NOT NULL,
            cost_usd REAL NOT NULL DEFAULT 0,
            verifier_passed INTEGER NOT NULL
        )
    ''')
    for row in rows:
        cur.execute(
            "INSERT INTO trajectory (request_id, tier, cost_usd, verifier_passed) VALUES (?, ?, ?, ?)",
            row
        )
    conn.commit()
    conn.close()

def test_load_db_metrics():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    try:
        # req1: attempts local then remote. passes on remote.
        # req2: attempt remote directly. passes.
        rows = [
            ("req1", "local", 0.0, 0),
            ("req1", "remote", 0.01, 1),
            ("req2", "remote", 0.015, 1)
        ]
        create_mock_db(db_path, rows)
        
        metrics = load_db_metrics(db_path)
        assert metrics["requests"] == 2
        assert metrics["total_attempts"] == 3
        assert metrics["remote_attempts"] == 2
        assert abs(metrics["remote_cost"] - 0.025) < 1e-6
        assert metrics["verified_rate"] == 100.0
    finally:
        os.remove(db_path)

def test_compare_runs():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as smoke_db:
        smoke_path = smoke_db.name
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as baseline_db:
        baseline_path = baseline_db.name
    with tempfile.TemporaryDirectory() as tmp_dir:
        output_prefix = os.path.join(tmp_dir, "test_out")
        
        try:
            # smoke: 1 req, 1 local attempt, 0 remote, cost 0
            create_mock_db(smoke_path, [("req1", "local", 0.0, 1)])
            
            # baseline: 1 req, 1 remote attempt, cost 0.01
            create_mock_db(baseline_path, [("req1", "remote", 0.01, 1)])
            
            compare_runs(smoke_path, baseline_path, output_prefix)
            
            json_file = output_prefix + ".json"
            md_file = output_prefix + ".md"
            
            assert os.path.exists(json_file)
            assert os.path.exists(md_file)
            
            with open(json_file, "r") as f:
                res = json.load(f)
                
            assert res["local_first"]["remote_attempts"] == 0
            assert res["always_remote"]["remote_attempts"] == 1
            assert res["comparison"]["remote_calls_avoided"] == 1
            assert res["comparison"]["remote_call_reduction_percentage"] == 100.0
            
            assert abs(res["comparison"]["configured_cost_avoided"] - 0.01) < 1e-6
            assert res["comparison"]["cost_reduction_percentage"] == 100.0
            
            assert res["caveats"] == CAVEATS
            
            with open(md_file, "r") as f:
                md_content = f.read()
                assert "Caveats" in md_content
                assert "100.0%" in md_content
        finally:
            os.remove(smoke_path)
            os.remove(baseline_path)
