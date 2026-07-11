import sqlite3
import argparse
import json
import os

CAVEATS = [
    "Configured-price estimate from recorded token counts, not provider invoice.",
    "Local-first smoke used mock local tier; AMD/Gemma proof is a separate measured artifact."
]

def load_db_metrics(db_path: str) -> dict:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT COUNT(DISTINCT request_id) as total_requests, COUNT(id) as total_attempts FROM trajectory")
    counts = cur.fetchone()
    total_requests = counts["total_requests"]
    total_attempts = counts["total_attempts"]

    cur.execute("SELECT COUNT(id) as remote_attempts, SUM(cost_usd) as total_cost FROM trajectory WHERE tier = 'remote'")
    remote_data = cur.fetchone()
    remote_attempts = remote_data["remote_attempts"] or 0
    total_cost = remote_data["total_cost"] or 0.0

    # For verified rate, we need to find if the LAST attempt per request_id had verifier_passed=1
    cur.execute("""
        SELECT request_id, verifier_passed
        FROM trajectory
        WHERE id IN (
            SELECT MAX(id)
            FROM trajectory
            GROUP BY request_id
        )
    """)
    last_attempts = cur.fetchall()
    verified_count = sum(1 for row in last_attempts if row["verifier_passed"] == 1)
    verified_rate = (verified_count / total_requests * 100.0) if total_requests > 0 else 0.0

    conn.close()

    return {
        "requests": total_requests,
        "total_attempts": total_attempts,
        "remote_attempts": remote_attempts,
        "remote_cost": total_cost,
        "verified_rate": verified_rate,
    }


def compare_runs(smoke_db_path: str, baseline_db_path: str, output_prefix: str):
    smoke_metrics = load_db_metrics(smoke_db_path)
    baseline_metrics = load_db_metrics(baseline_db_path)

    remote_calls_avoided = baseline_metrics["remote_attempts"] - smoke_metrics["remote_attempts"]
    if baseline_metrics["remote_attempts"] > 0:
        remote_call_reduction_pct = (remote_calls_avoided / baseline_metrics["remote_attempts"]) * 100.0
    else:
        remote_call_reduction_pct = 0.0

    cost_avoided = baseline_metrics["remote_cost"] - smoke_metrics["remote_cost"]
    if baseline_metrics["remote_cost"] > 0:
        cost_reduction_pct = (cost_avoided / baseline_metrics["remote_cost"]) * 100.0
    else:
        cost_reduction_pct = 0.0

    results = {
        "local_first": {
            "requests": smoke_metrics["requests"],
            "total_attempts": smoke_metrics["total_attempts"],
            "remote_attempts": smoke_metrics["remote_attempts"],
            "total_configured_remote_cost": smoke_metrics["remote_cost"],
            "final_verified_rate": smoke_metrics["verified_rate"]
        },
        "always_remote": {
            "requests": baseline_metrics["requests"],
            "total_attempts": baseline_metrics["total_attempts"],
            "remote_attempts": baseline_metrics["remote_attempts"],
            "total_configured_remote_cost": baseline_metrics["remote_cost"],
            "final_verified_rate": baseline_metrics["verified_rate"]
        },
        "comparison": {
            "remote_calls_avoided": remote_calls_avoided,
            "remote_call_reduction_percentage": remote_call_reduction_pct,
            "configured_cost_avoided": cost_avoided,
            "cost_reduction_percentage": cost_reduction_pct
        },
        "caveats": CAVEATS
    }

    # Write JSON
    json_path = f"{output_prefix}.json"
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)
    
    # Write Markdown
    md_path = f"{output_prefix}.md"
    with open(md_path, "w") as f:
        f.write("# Fireworks Cost Comparison\n\n")
        f.write("## Local-First (Escalation Smoke)\n")
        f.write(f"- Requests: {results['local_first']['requests']}\n")
        f.write(f"- Total Attempts: {results['local_first']['total_attempts']}\n")
        f.write(f"- Remote Attempts: {results['local_first']['remote_attempts']}\n")
        f.write(f"- Remote Cost: ${results['local_first']['total_configured_remote_cost']:.6f}\n")
        f.write(f"- Final Verified Rate: {results['local_first']['final_verified_rate']:.1f}%\n\n")
        
        f.write("## Always-Remote (Baseline)\n")
        f.write(f"- Requests: {results['always_remote']['requests']}\n")
        f.write(f"- Total Attempts: {results['always_remote']['total_attempts']}\n")
        f.write(f"- Remote Attempts: {results['always_remote']['remote_attempts']}\n")
        f.write(f"- Remote Cost: ${results['always_remote']['total_configured_remote_cost']:.6f}\n")
        f.write(f"- Final Verified Rate: {results['always_remote']['final_verified_rate']:.1f}%\n\n")

        f.write("## Comparison Metrics\n")
        f.write(f"- **Remote Calls Avoided**: {results['comparison']['remote_calls_avoided']}\n")
        f.write(f"- **Remote Call Reduction**: {results['comparison']['remote_call_reduction_percentage']:.1f}%\n")
        f.write(f"- **Configured Cost Avoided**: ${results['comparison']['configured_cost_avoided']:.6f}\n")
        f.write(f"- **Cost Reduction**: {results['comparison']['cost_reduction_percentage']:.1f}%\n\n")

        f.write("## Caveats\n")
        for caveat in CAVEATS:
            f.write(f"- {caveat}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compare two Fireworks trajectory runs")
    parser.add_argument("--smoke-db", required=True, help="Path to local-first smoke db")
    parser.add_argument("--baseline-db", required=True, help="Path to always-remote baseline db")
    parser.add_argument("--output-prefix", required=True, help="Prefix for output JSON/MD files")
    args = parser.parse_args()

    compare_runs(args.smoke_db, args.baseline_db, args.output_prefix)
    print(f"Generated {args.output_prefix}.json and {args.output_prefix}.md")
