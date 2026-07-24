# App screenshots

Drop three PNGs here and they'll appear in the top-level README:

| File                   | View to capture   | How to get there                          |
| ---------------------- | ----------------- | ----------------------------------------- |
| `dashboard.png`        | Dashboard         | landing page                              |
| `beam-optimizer.png`   | Beam Optimizer    | run a sweep so the results table + plot show |
| `bracket-analysis.png` | Bracket Analysis  | evaluate a bracket so the checks render   |

## Capture them

Start the app (one server serves everything):

```bash
cd frontend && npm run build
cd ../mechopt && uv run --extra api uvicorn api:app --port 8000
```

Open <http://localhost:8000>, size the window to ~1440×900, and screenshot each view.
On Windows, **Win+Shift+S** crops to a region; save the PNGs into this folder with the
names above.

Then reference them in `README.md` (the "Screenshots" section already has a placeholder
note), commit, and push.
