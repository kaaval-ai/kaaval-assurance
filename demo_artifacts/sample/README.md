# Sample demo artifacts

Synthetic sample data for the demo console (`apps/demo_console/`), generated
by the mock pipeline with zero cloud access: mock local tier with injected
failures, mock remote tier, mock audit challenger calibrated against the gold
answers. Runtime status in this data is `planned` — nothing here claims a
measured AMD runtime.

These files exist so the console runs anywhere without secrets or AMD access.
Real artifacts written to `artifacts/` by the runtime probe and eval CLI on
the AMD pod take precedence automatically.
