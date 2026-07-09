# Demo console

Streamlit replay surface for Kaaval Assurance telemetry.

Run locally:

```bash
pip install -e ".[demo]"
streamlit run apps/demo_console/app.py
```

Hosted deployment (Streamlit Community Cloud or Hugging Face Spaces): see
[docs/hosted-demo.md](../../docs/hosted-demo.md). No secrets required — the
console only reads recorded JSON/markdown artifacts.

Artifact loading order: `artifacts/` first (real recorded runs), then
`demo_artifacts/sample/` as fallback.

Honesty note: the shipped sample data is synthetic (mock providers, zero
cloud access) and its runtime status is `planned`. It stays that way until
measured artifacts from the AMD pod run are copied into `artifacts/`.
