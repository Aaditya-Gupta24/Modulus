# Modulus — engine & API

Python project root for **Modulus**. This directory holds the mechanics engine
(`modulus/`), the FastAPI layer (`api.py`), the independent FE validation suite
(`validation/`), and the tests. For the full project overview, screenshots, and deploy
guide, see the [repository README](../README.md).

## The engine

`modulus/` is a pure-Python + NumPy library with no web dependencies:

- **Mechanics** — `materials`, `sections`, `beam`, `buckling`, `bracket`
- **Decision** — `optimizer` (design-space sweep), `decision` (rank / Pareto / knee),
  `failure_modes`, `design_review`
- **Rigor** — `uncertainty` (Monte-Carlo), `envelope` (load cases), `stock` (buyable
  sizes), `units`
- **Output** — `report` (CSV/JSON/PDF), `visuals` (SVG diagrams)

`api.py` wraps the engine as a JSON API and, when `../frontend/build` exists, serves the
built React SPA from the same origin (single-service deployment).

## Run

```bash
uv run --extra api python api.py         # API at http://localhost:8000
uv run --extra dev pytest -q             # 357 passing
uv run python validation/run_validation.py   # reproduce the FE validation report
```

No `uv`? `pip install -e ".[api,dev]"` then `python api.py` / `pytest -q`.

## Validation

The analytical model matches an independent from-scratch 1-D finite-element solver
(`validation/fea_beam.py`, direct stiffness, Hermite cubic elements) to **< 0.01 %**, and
Euler–Bernoulli vs. Timoshenko shear error stays **< 0.4 %** for slender beams. Full
report: [`validation/VALIDATION.md`](validation/VALIDATION.md).

## License

MIT © 2026 Aaditya Gupta
