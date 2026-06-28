# MechOpt — Multi-Phase Looped Prompt: Section Coverage + UI Polish + Context Refresh

Paste the **RULES** block plus **one phase at a time** into Claude Code, run from
`C:\Users\AADITYA GUPTA\OneDrive\Desktop\MechOpt\mechopt`. Do not paste all phases at
once — each phase has its own exit criteria and you should confirm green before moving on.

> **Reality check before you start (read this once).**
> All six section types named for this loop **already exist** in `mechopt/mechopt/sections.py`
> (`rectangle`, `circle`, `i_beam`, `square_tube`, `hollow_rectangle`, `hollow_circle`) and are
> already swept by `optimizer.evaluate_candidates`. All six materials (incl. titanium, brass, abs)
> are in `materials.py`. So this loop is **not** "write brand-new physics" — it is:
> (1) guarantee every section has oracle-grade test coverage, (2) surface all six sections in
> `index.html` to the screenshot standard, (3) keep `index.html`'s JavaScript physics in exact
> parity with the Python oracle, (4) refresh the stale `PROJECT_CONTEXT.md`.
> UI label ↔ code name map: **Sq. Tube** = `square_tube`, **Box Tube** = `hollow_rectangle`,
> **Round Tube** = `hollow_circle`, **I-Beam** = `i_beam`.

---

## RULES (apply to every phase)

1. **The tests in `tests/` are the oracle.** Never edit, loosen, delete, skip, `xfail`, or
   widen the tolerance of a verified numeric target to make a test pass. Fix the code, never
   the answer key.
2. **Any new numeric target must be DERIVED from the equation**, with the substitution shown
   in a comment, and printed once for spot-check. Never copy a number out of code output and
   call it a target — that turns the oracle into an echo.
3. **Don't change existing public signatures** (`sections.*`, `beam.*`, `optimizer.*`,
   `bracket.*`). If a signature legitimately must change, the asserted physical value stays
   identical; STOP and ask if a change would alter any verified target.
4. **Loop discipline:** after every change run `pytest -q`, read the failure, fix the code,
   repeat until green. Show the failing assertion before you fix it.
5. **`index.html` has no pytest.** Its oracle is the Python result for the same inputs. Any
   number the HTML displays for a shared case must match the Python module to the displayed
   precision. When in doubt, compute it in Python and compare.
6. Work autonomously inside a phase; stop at the phase's **EXIT** gate and report.

### Verified oracle numbers (hand-derived — safe to assert)

```
Sections (SI):
  square_tube(a=0.040, w=0.004)         A=5.760000e-4  I=1.259520e-7  c=0.020
  hollow_rectangle(b=.040,h=.060,w=.004) A=7.360000e-4  I=3.450453e-7  c=0.030
  hollow_circle(d=0.050, di=0.042)      A=5.780530e-4  I=1.540511e-7  c=0.025
  i_beam(b=.050,h=.100,tf=.008,tw=.006) A=1.304000e-3  I=1.993419e-6  c=0.050
  Solid-limit identity: hollow_circle(d, di=0) == circle(d) ; square_tube(a, w=a/2)->0 area

Beam Case A — steel_a36, square 30x30, L=0.8, P=300, cantilever_end:
  I=6.75e-8   sigma=53.333 MPa   delta=3.7926 mm   FoS=4.6875
Beam Case B — aluminum_6061, circle d=30, L=1.2, P=800, simply_center:
  I=3.97608e-8  sigma=90.541 MPa  delta=10.4976 mm  FoS=3.0373
```

(Section equations: square_tube ai=a−2w, A=a²−ai², I=(a⁴−ai⁴)/12, c=a/2 ·
hollow_rectangle bi=b−2w, hi=h−2w, A=bh−bihi, I=(bh³−bihi³)/12, c=h/2 ·
hollow_circle A=π(d²−di²)/4, I=π(d⁴−di⁴)/64, c=d/2 ·
i_beam A=bh−(b−tw)(h−2tf), I=(bh³−(b−tw)(h−2tf)³)/12, c=h/2.)

---

## PHASE 1 — Lock down section coverage (oracle-first)

GOAL: every section type in this loop (`square_tube`, `hollow_rectangle`, `hollow_circle`,
`i_beam`) has complete, independently-derived test coverage, and the optimizer sweeps all of them.

Steps:
1. Read `SPEC.md` and `tests/test_sections.py` in full. List which of the four sections already
   have a verified-target test and which assertions exist (props, edge cases, errors).
2. For any **missing** coverage, add tests using the verified numbers above. Each new test:
   asserts `A`, `I`, `c` to a tight `rel=1e-6`; includes a comment with the equation substitution;
   prints the derived target once.
3. Add these property/sanity tests if absent (all derivable, not echoed):
   - **Solid-limit identity:** `hollow_circle(d, 0).I == circle(d).I` and `.A`, `.c` too.
   - **Monotonicity:** for fixed outer size, increasing wall thickness `w` decreases `I`
     (assert ordering, not magnitudes — this is a property, not a target).
   - **ValueError on invalid geometry:** wall ≥ half the outer dimension; inner ≥ outer
     (`hollow_circle(d, di>=d)`); non-positive dimensions. Add `raises(ValueError)` only if the
     code is *meant* to raise — if it doesn't yet, add the guard in `sections.py` (fix the code).
4. Confirm `optimizer.evaluate_candidates` sweeps all four when requested via `section_types`,
   and that each emitted row has the exact column contract (`material, section, dims, area, I,
   weight, cost, stress, deflection, fos, safe`). Add an optimizer test that asks for a single
   section type and asserts only that `section` value appears.
5. `pytest -q` → green.

EXIT: `pytest -q` green; report the test count before/after and list every new target with its
substitution. Do not touch `index.html` in this phase.

---

## PHASE 2 — Bring `index.html` to the screenshot standard

GOAL: `index.html` is a single self-contained file (no Streamlit, no build step) that matches
the reference UI: dark theme, four tabs (**Beam Optimizer · Bracket Analysis · Compare Designs ·
Assumptions**), and on the Beam tab — a Loading panel, Objective priority buttons
(**Balanced / Lightest / Cheapest / Safest**), Materials toggles, **all six** Cross-section
toggles, a Recommended card, two tradeoff scatter plots, and a candidates table.

Hard requirements:
1. **All six cross-section toggles present and wired:** Rectangle, Circle, I-Beam, Sq. Tube,
   Box Tube, Round Tube. Toggling one adds/removes its candidates from the sweep, the plots, and
   the table live. Confirm Box Tube (`hollow_rectangle`) and Round Tube (`hollow_circle`) are not
   missing — the current file references `square_tube` and `hollow` but verify both tubes render
   as labeled buttons.
2. **Recommended card** mirrors the screenshot: material name + section + dims; tiles for
   Factor of Safety (with "+x vs target"), Max Stress (with "σy NNN MPa"), Deflection
   (or "no limit"), Weight (per chosen length), Cost ("material only"); a small to-scale SVG of
   the section; a Controls/"governing limit" line; and a one-line natural-language rationale
   ("Selected as the Balanced safe option from N safe of M total candidates…").
3. **Objective buttons** actually re-rank: Lightest = min weight among safe; Cheapest = min cost
   among safe; Safest = max FoS; Balanced = normalized weight+cost+FoS blend. Match the Python
   `optimizer.recommend` definitions so the two implementations never disagree.
4. **Two scatter plots:** Weight vs FoS and Cost vs FoS, colored by material, the recommended
   point highlighted, with a dashed FoS-target line. Pure SVG/canvas or a single CDN lib only.
5. **Candidates table:** Material, Section, Dims, FoS, Σ MPa, Δ mm, KG, $, OK — sortable, with a
   "Show all / N safe of M total" toggle.
6. **Physics parity (the correctness gate):** the JS that computes A, I, σ, δ, FoS, weight, cost
   must reproduce the Python oracle. Verify by running, in Python, the exact inputs from the
   screenshot default (Aluminum 6061, Rectangle 30×30, L=1.0 m, P=500 N, cantilever) and
   confirming the card's numbers match (FoS, MPa, mm, kg, $) to the shown precision. Then check
   one tube case and one I-beam case the same way. If any disagree, fix the JS — the Python module
   is the oracle.

Because the handshake/UI can't be unit-tested, **verify by serving the file** (`python -m http.server`
in the git root) and reading the rendered numbers; keep `pytest` green throughout (Phase-2 work
must not touch Python physics in a way that breaks Phase-1 targets).

EXIT: all six section toggles work; card + plots + table match the reference; JS numbers match the
Python oracle for the three checked cases; `pytest -q` still green. Report the three parity checks
with both numbers side by side.

---

## PHASE 3 — Refresh `PROJECT_CONTEXT.md`

GOAL: `PROJECT_CONTEXT.md` describes the **current** repo, not the old scaffold.

Steps:
1. Replace the "Current status: STUBS / NotImplementedError" section with the real state: core
   implemented and passing; sections = rectangle, circle, i_beam, square_tube, hollow_rectangle,
   hollow_circle; materials = aluminum_6061, steel_a36, pla, titanium_ti6al4v, brass_360,
   abs_plastic; `bracket.py` present; `app.py` = 4-tab Streamlit UI; `index.html` = standalone
   dashboard; test count from `pytest --co -q`.
2. Update the **Tracked files** tree from `git ls-files` (add `bracket.py`, `index.html`,
   `test_bracket.py`; drop anything no longer present).
3. Move titanium/brass/abs out of "Proposed additions" into "Implemented." Same for the tube/
   i-beam sections — they're done, not stubbed.
4. Keep the engineering-equations and verified-oracle-targets blocks verbatim (still valid).
5. Add an `index.html` subsection: standalone no-Streamlit dashboard, served locally via
   `python -m http.server`, JS physics kept in parity with the Python oracle (note the parity rule).
6. Add a pointer to `LOOPED_PROMPT.md` and update "Immediate next step."
7. Re-derive nothing; this phase is documentation only. Do not let it change code or tests.

EXIT: `PROJECT_CONTEXT.md` matches `git ls-files` and the actual module contents; a fresh reader
could resume with no surprises. Commit all three phases with a clear message and push.
