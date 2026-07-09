import json
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Kaaval Assurance Telemetry API")

# Allow CORS for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "artifacts"
SAMPLE = ROOT / "demo_artifacts" / "sample"

def _load_artifact(name: str):
    """Prefer real artifacts/, fall back to shipped sample data."""
    for base in (ARTIFACTS, SAMPLE):
        path = base / name
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
    return None

@app.get("/api/telemetry")
def get_telemetry():
    data = _load_artifact("telemetry-truth.json")
    if data is None:
        raise HTTPException(status_code=404, detail="Telemetry artifact not found")
    return data

@app.get("/api/trajectory")
def get_trajectory():
    data = _load_artifact("trajectory-sample.json")
    if data is None:
        raise HTTPException(status_code=404, detail="Trajectory artifact not found")
    return data

@app.get("/api/runtime-probe")
def get_runtime_probe():
    data = _load_artifact("runtime-probe.json")
    if data is None:
        raise HTTPException(status_code=404, detail="Runtime probe artifact not found")
    return data

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("apps.api.server:app", host="127.0.0.1", port=8000, reload=True)
