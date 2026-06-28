# MechOpt — Project Context / Chat Handoff

Paste this whole file into a new chat to continue with full context.
_Last refreshed: 2026-06-15 (status updated from "stubs" to implemented; verified against `git ls-files` and module contents)._

## What the project is
**MechOpt — Python-Based Mechanical Design Optimization Tool.** A sophomore-level
mechanical-engineering resume project, fully online. It screens beam and bracket
designs across material, cross-section, and dimensions, then recommends the best
design under a chosen priority (lightest safe / cheapest safe / highest FoS /
best-balanced) and plots the weight–cost–strength tradeoffs.

Owner: Aaditya (GitHub: Aaditya-Gupta24). Stack: Python, numpy, pandas,
matplotlib/plotly, streamlit, pytest (scipy.optimize planned later).

## Where things live
- Local git root: `C:\Users\AADITYA GUPTA\OneDrive\Desktop\MechOpt`
- GitHub remote: https://github.com/Aaditya-Gupta24/MechOpt.git
- Default branch: `master`, in sync with `origin/master` at the
  `feat: implement full MechOpt design screening dashboard` commit.
- The project is nested one level down: the Python package and config live in
  `C:\Users\AADITYA GUPTA\OneDrive\Desktop\MechOpt\mechopt\` (this is the
  "project root" where `SPEC.md` and `pytest.ini` live).
- `LICENSE` (MIT, © 2026 Aaditya Gupta), `index.html`, `PROJECT_CONTEXT.md`, and
  `LOOPED_PROMPT.md` are at the **git root**.

### Known structural notes / open decisions
- The repo is nested: `MechOpt/mechopt/<everything>`. User chose NOT to flatten.
- Because of the nesting, the CI workflow at `mechopt/.github/workflows/ci.yml`
  will NOT run on GitHub — Actions only runs workflows in `.github/` at the
  REPOSITORY ROOT. To turn CI on, either flatten the repo or move `.github` to
  the git root. (Still deferred.)
- OneDrive sync can make `git status` look noisy (cloud-only files show as
  "deleted"); the committed/pushed tree is the source of truth.

## Current status — IMPLEMENTED (no longer stubs)
The core library is fully implemented and matches the hand-verified oracle numbers
(spot-checked: Beam Case A and all four section targets are exact). A 4-tab Streamlit
app and a standalone `index.html` dashboard are both built and committed.

What's done:
- **`sections.py`** — `rectangle`, `circle`, `i_beam`, `hollow_rectangle`,
  `square_tube`, `hollow_circle` (all implemented, all verified).
- **`beam.py`** — `max_moment`, `max_stress`, `max_deflection`, `factor_of_safety`.
- **`optimizer.py`** — `evaluate_candidates` (brute-force sweep, sweeps all six
  sections) + `recommend` (lightest / cheapest / safest / balanced).
- **`bracket.py`** — simplified wall-mounted bracket (plate bending + bolt group),
  `evaluate_bracket`, controlling-constraint logic.
- **`materials.py`** — all six materials (see below).
- **`app.py`** — Streamlit UI, 4 tabs: Beam Optimizer, Bracket Analysis,
  Compare Designs, Assumptions & Limitations.
- **`index.html`** — standalone, self-contained dark-theme dashboard (no Streamlit,
  no build step) mirroring the app; served locally via `python -m http.server`.
- **Tests** — `test_sections.py` (13), `test_beam.py` (3), `test_bracket.py` (9),
  `test_optimizer.py` (6) ≈ 31 tests. (Re-confirm with `pytest --co -q`.)

What's open: refresh CI so it runs on GitHub; deploy live on Streamlit Community
Cloud; clean README; then the Week 2–4 roadmap (buckling, deflection limit,
asymmetric sections, scipy optimization, FEA validation, technical report).

### Tracked files (`git ls-files`)
```
LICENSE                              (git root)
index.html                           (git root — standalone dashboard)
PROJECT_CONTEXT.md                   (git root — this file)
LOOPED_PROMPT.md                     (git root — multi-phase looped prompt)
mechopt/.github/workflows/ci.yml     (won't run — nested, see note above)
mechopt/.gitignore
mechopt/README.md
mechopt/SPEC.md
mechopt/app.py                       (DONE — 4-tab Streamlit UI)
mechopt/pytest.ini
mechopt/requirements.txt
mechopt/mechopt/__init__.py
mechopt/mechopt/materials.py         (DONE — 6 materials)
mechopt/mechopt/sections.py          (DONE — 6 sections)
mechopt/mechopt/beam.py              (DONE)
mechopt/mechopt/optimizer.py         (DONE)
mechopt/mechopt/bracket.py           (DONE)
mechopt/tests/test_sections.py
mechopt/tests/test_beam.py
mechopt/tests/test_bracket.py
mechopt/tests/test_optimizer.py
```

### The `index.html` dashboard (UI standard)
Standalone HTML/CSS/JS file — no Streamlit dependency, opens in any browser or via a
local server. It re-implements the screening physics in JavaScript so it runs
client-side. **Parity rule:** any number `index.html` displays for a given input must
match the Python module's result for the same input (the Python module is the oracle;
the HTML has no pytest). Target UI: four tabs (Beam Optimizer / Bracket Analysis /
Compare Designs / Assumptions); on the Beam tab — Loading inputs, Objective priority
buttons (Balanced/Lightest/Cheapest/Safest), Materials toggles, six Cross-section
toggles (Rectangle, Circle, I-Beam, Sq. Tube, Box Tube, Round Tube), a Recommended
card (FoS / max stress / deflection / weight / cost tiles + to-scale SVG + governing
limit + rationale), two tradeoff scatter plots (Weight vs FoS, Cost vs FoS), and a
sortable candidates table. UI-label ↔ code-name map: Sq. Tube=`square_tube`,
Box Tube=`hollow_rectangle`, Round Tube=`hollow_circle`, I-Beam=`i_beam`.

## Core methodology: "loop engineering"
The **test suite in `tests/` is the correctness oracle.** Tests hardcode
hand-verified numbers DERIVED FROM THE EQUATIONS (not copied from code output).
The loop's job: keep `pytest` green without ever editing a verified numeric target.
A loop that can edit its own answer key is not an oracle. **Rule: fix the code,
never the test target.** See `LOOPED_PROMPT.md` for the current multi-phase loop.

Setup to run the loop (in a terminal):
```
cd "C:\Users\AADITYA GUPTA\OneDrive\Desktop\MechOpt\mechopt"
pip install -r requirements.txt
pytest -q          # confirm green baseline
claude
```

## Engineering equations (the physics)
Sections (return area A, second moment I, outer-fibre distance c):
- rectangle: A=b·h, I=b·h³/12, c=h/2
- circle: A=π·d²/4, I=π·d⁴/64, c=d/2
- hollow_rectangle (outer b,h; wall w): bi=b−2w, hi=h−2w; A=b·h−bi·hi; I=(b·h³−bi·hi³)/12; c=h/2
- hollow_circle (outer d, inner di): A=π(d²−di²)/4; I=π(d⁴−di⁴)/64; c=d/2
- square_tube (outer a, wall w): ai=a−2w; A=a²−ai²; I=(a·a³−ai·ai³)/12; c=a/2
- i_beam (b,h,tf,tw): A=b·h−(b−tw)(h−2tf); I=(b·h³−(b−tw)(h−2tf)³)/12; c=h/2

Beam (load cases):
- cantilever_end: M=P·L, δ=P·L³/(3·E·I)
- simply_center:  M=P·L/4, δ=P·L³/(48·E·I)
- σ = M·c/I ; FoS = σ_y/σ ; weight=A·L·ρ ; cost=weight·cost_per_kg

Bracket (L-bracket = cantilever arm + shear at the root):
- M=P·L, σ_b=M·c/I, τ_avg=P/A, σ_vm=√(σ_b²+3·τ_avg²), δ=P·L³/(3·E·I), FoS=σ_y/σ_vm
- (σ_vm here = conservative screen; peak bending & avg shear don't occur at the same point — documented as a limitation.)

Planned later (month-2 depth): Euler buckling P_cr=π²·E·I/(K·L)²; deflection-limit
constraint (e.g. δ ≤ L/360); asymmetric sections (T, L/angle) needing neutral-axis
location ȳ=ΣAᵢȳᵢ/ΣAᵢ + parallel-axis theorem (c ≠ h/2).

## Materials (SI: E[Pa], σ_y[Pa], ρ[kg/m³], cost[USD/kg]) — IMPLEMENTED
All six are in `materials.py` (cost is relative/illustrative, document in README):
- aluminum_6061 (Aluminum 6061-T6): E=69e9,  σ_y=275e6, ρ=2700, cost=3.5
- steel_a36 (Steel A36):            E=200e9, σ_y=250e6, ρ=7850, cost=1.0
- pla (PLA 3D print):               E=3.5e9, σ_y=50e6,  ρ=1240, cost=25.0
- titanium_ti6al4v (Ti-6Al-4V):     E=114e9, σ_y=880e6, ρ=4430, cost=35.0
- brass_360 (Brass C360):           E=100e9, σ_y=125e6, ρ=8500, cost=6.0
- abs_plastic (ABS 3D print):       E=2.3e9, σ_y=40e6,  ρ=1050, cost=20.0

## HAND-VERIFIED test targets (the oracle numbers — all independently computed)
Beam Case A — steel_a36, square 30×30 mm, L=0.8 m, P=300 N, cantilever_end:
  I=6.75e-8 m⁴, σ=53.333 MPa, δ=3.7926 mm, FoS=4.6875
Beam Case B — aluminum_6061, circle d=30 mm, L=1.2 m, P=800 N, simply_center:
  I=3.97608e-8 m⁴, σ=90.541 MPa, δ=10.4976 mm, FoS=3.0373
Bracket BR-1 — steel_a36, b=40 t=8 mm, L=100 mm, P=500 N:
  I=1.70667e-9 m⁴, σ_b=117.1875 MPa, τ=1.5625 MPa, σ_vm=117.219 MPa, δ=0.4883 mm, FoS=2.1328
Bracket BR-2 — aluminum_6061, b=50 t=6 mm, L=120 mm, P=400 N:
  I=9.000e-10 m⁴, σ_b=160.000 MPa, τ=1.3333 MPa, σ_vm=160.017 MPa, δ=3.7101 mm, FoS=1.7186
Section props:
  hollow_rectangle b40 h60 w4: A=7.36000e-4, I=3.450453e-7, c=0.030
  hollow_circle    d50 di42:   A=5.780530e-4, I=1.540511e-7, c=0.025
  square_tube      a40 w4:     A=5.760000e-4, I=1.259520e-7, c=0.020
  i_beam b50 h100 tf8 tw6:     A=1.304000e-3, I=1.993419e-6, c=0.050

## Reusable loop prompt
The active multi-phase loop lives in **`LOOPED_PROMPT.md`** (git root): Phase 1 locks
down section-type oracle coverage, Phase 2 brings `index.html` to the reference UI
standard with all six section toggles + JS↔Python parity, Phase 3 keeps this context
file current. Shared RULES: never weaken/edit a verified target; derive any new target
from the equation and print it; fix the code, not the tests; `pytest -q` after every
change.

## Month-long roadmap (depth over breadth; validation is the differentiator)
- Week 1 — Foundation: core green ✅, app + index.html built ✅. Remaining: CI passing,
  app deployed live on Streamlit Community Cloud, clean README.
- Week 2 — Deeper mechanics: Euler buckling, deflection-limit constraint, asymmetric
  T/L sections (neutral-axis + parallel-axis). Verified targets each.
- Week 3 — Real optimization + validation: scipy.optimize continuous design, Pareto
  fronts, and VALIDATE analytical model against a simple FEA / independent method
  (the single most impressive thing — "matched FEA within X%").
- Week 4 — Communication: technical-report PDF built around one design case study,
  sensitivity/parametric analysis, demo GIF, notebook walkthrough, limitations section.

Interview talking points to earn: "validated against FEA within X%"; "optimizer
picks tubes for light designs because material far from the neutral axis carries
bending — here's the Pareto front"; "it's a screening tool — no fatigue, buckling
interaction, or stress concentrations."

## Immediate next step
Run `LOOPED_PROMPT.md` Phase 1 → 2 → 3 from `MechOpt\mechopt`. Before trusting the
suite, hand-check one target (e.g. Beam Case A: σ=M·c/I with M=300×0.8, I=0.03⁴/12).
After the loop, tackle Week-1 leftovers: CI at repo root + live Streamlit deploy + README.
```
```
