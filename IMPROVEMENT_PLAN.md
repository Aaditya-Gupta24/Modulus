# MechOpt — Improvement Plan (from the Passion-Project Review)

_Plan only. No code written yet. Companion to `PROJECT_CONTEXT.md` and `LOOPED_PROMPT.md`._
_Source: `passion_project_improvement_report.pdf` (Summer Passion Project Review). Drafted 2026-06-29._

---

## 0. The thesis (what "special" means)

> Stop being "a beam calculator with a Streamlit UI." Become a **transparent design
> cockpit** that doesn't just calculate — it **justifies, compares, warns, and validates.**

Niche = clarity, speed, openness, educational value, decision traceability. **Do not**
chase Ansys-level fidelity. **Do not** bloat: no 3D FEA from scratch, no AI chatbot, no
huge unsourced material DB, no exotic sections, no code-compliance claims. The project
gets special by being **trustworthy**, not big.

Every milestone below is justified by that thesis and maps to the report's own 5-phase
roadmap (§19).

---

## 1. Reality check against the current code

What the review asks for, versus what's actually in the repo today:

| Review ask | Current code reality | Gap |
|---|---|---|
| Return ranked options, not one winner (§2) | `optimizer.recommend()` returns a single `pd.Series` | Add ranking / Pareto / alternatives layer |
| Pareto front, knee-point, why-won (§2) | none | New functions over existing candidate DataFrame |
| Wire buckling into UI + per-candidate safety case (§3) | `buckling.py` complete & tested but called **nowhere**; `safe` is an inline bool computed 6× | Integrate + replace bool with a safety case |
| Modular failure modes (§16) | `evaluate_candidates` copy-pastes one ~13-line eval block **6 times** | The enabling refactor |
| Why-not explanations (§10) | `safe=False` carries no reason | Falls out of the safety-case object |
| Bracket gusset variants + bolt bearing/tear-out/edge (§4, §8) | plate-bending + `sqrt(τ²+σ²)` bolt combine; `bolt_group_loads` is a dead `NotImplementedError` stub | New bracket geometry + bolt checks |
| Manufacturing / standard stock (§5) | sweep is hardcoded `np.arange(10,110,10)` | Stock libraries + nearest-buyable |
| Uncertainty / Monte Carlo (§6) | all inputs treated as exact | New robustness mode |
| Load-case envelopes (§7) | one load case per run | Multi-case governing logic |
| Design Review Mode (§18) | none | Text layer over §2+§3 data |
| Units system (§15) | SI internally, ad-hoc display | Optional unit-IO layer |
| 3 case studies + physical test + PDF report (§11–13) | 1 case study (`docs/CASE_STUDY.md`) + FE validation exist | Extend, don't restart |

**Key efficiency insight:** five separate review items (§3 safety-case table, §10 why-not,
the §2 constraint-breakdown, §18 Design Review, and future shear/torsion) are all blocked
on the *same* missing abstraction. Build that abstraction once (Milestone A) and they
become cheap presentation layers instead of five independent features.

---

## 2. Build order (highest-leverage first)

Sequenced for dependency + leverage, not in the report's numbering. Each milestone is
independently shippable and keeps the suite green.

### Milestone A — Modular `FailureMode` spine `[ENABLER, do first]`
_Report §16 + §3. The force multiplier._

- New `mechopt/failure_modes.py`. Define a uniform check result:
  `CheckResult(name, actual, allowable, margin, status, notes)` where `status ∈
  {pass, fail, warning, not_modeled}`.
- Each check is a small function/class: `bending_stress`, `deflection`, `euler_buckling`
  (wraps existing `buckling.py`), plus declared-but-`not_modeled` stubs for `shear` and
  `torsion` that emit a **warning** row (honesty, per §3/§14).
- New `evaluate_candidate(material, section, dims, load, length, load_case, targets)` →
  runs the registry, returns the row **plus** a `SafetyCase` (list of `CheckResult` +
  overall status + controlling constraint + failure reason).
- **Refactor `optimizer.evaluate_candidates`** to call this once per candidate. Collapses
  the 6 duplicated blocks into one loop. `safe` boolean stays as a derived column for
  backward-compat so existing tests/app keep working.
- **Tests (oracle-first):** `test_failure_modes.py`. Re-derive every margin/status by hand
  from the equations (never edit a target to pass). Existing 6 `test_optimizer` cases must
  still pass unchanged — that's the refactor's safety net.
- **Done when:** `evaluate_candidates` output is byte-identical on the existing columns,
  the duplication is gone, and each candidate carries a `SafetyCase`.

### Milestone B — Buckling in the UI + safety-case table `[visible win]`
_Report §3. "Replace safe:true/false with a safety case."_

- Surface the per-candidate failure-mode table in the app (Check / Value / Limit / Margin /
  Status), driven entirely by Milestone A's `SafetyCase` — no new mechanics.
- Add the optimizer-sweep buckling pass (needs a compression-load input + end-condition K
  selector in the UI). Buckling joins the safety case for compression cases.
- Shear & torsion show as explicit **"not modeled — warning"** rows.
- **Tests:** extend `test_buckling` integration + an app-helper test that the table renders
  the right rows/status for a known candidate (oracle numbers in `PROJECT_CONTEXT.md §7`).

### Milestone C — Decision intelligence: ranked options + Pareto + knee `[report's #1]`
_Report §2. Pure pandas over the existing DataFrame; no new physics._

- New functions in `optimizer.py` (or `decision.py`):
  `rank_candidates(df, priority)`, `pareto_front(df, objectives=[weight,cost,fos,deflection])`,
  `knee_point(front)`, `classify_infeasible(df)` → reason per failed row
  (`failed_stress | failed_deflection | failed_buckling | invalid_geometry`),
  `explain_winner(row, safety_case)` → "wins because deflection, not stress, is active…".
- App: replace single recommendation card with a **ranked top-N table** (Why-good / What-
  controls / Risk columns, exactly like the report's table), a Pareto scatter, and a
  constraint-breakdown summary of *why the rejected designs failed* (§10 why-not).
- **Tests:** `test_decision.py` — dominance filtering on a tiny hand-built frame with a
  known Pareto set and known knee index. All targets hand-derived.
- **Done when:** the app shows a decision landscape, not one answer.

### Milestone D — Design Review Mode `[the "special feature" capstone]`
_Report §18. A text/layout layer over A–C; cheap once they exist._

- New `design_review.py`: `generate_review(winner, safety_case, alternatives,
  sensitivities)` → structured object → rendered block: **Recommended design / Why it won /
  Controlling constraint / Most important sensitivity / Risks (unmodeled) / Nearest
  practical alternative / Recommended next step.**
- "Most important sensitivity" = a cheap one-at-a-time finite-difference on the winner
  (bump height vs wall thickness, see which moves FoS/deflection more) — not full Monte
  Carlo yet.
- **Tests:** assert the review names the correct controlling constraint and lists the
  correct unmodeled risks for the `PROJECT_CONTEXT §7` oracle beams.
- **Done when:** the app reads like a junior engineer's design review.

> **A–D is the "feels special" core.** If the summer stalls after D, the project is already
> transformed. E–H below are the realism/evidence layers.

### Milestone E — Manufacturing realism (standard stock) `[Phase 4]`
_Report §5._

- `stock.py`: metric plate thicknesses (1, 1.5, 2, 3, 4, 5, 6, 8, 10), common tube/rod
  sizes, bolt sizes (M3–M10). Add a **design-mode toggle**: "conceptual sweep" vs
  "standard stock only."
- `nearest_buyable(theoretical_design)` → "+14% mass, +31% stiffness" comparison.
- **Tests:** snapping logic + penalty math on known cases.

### Milestone F — Bracket as hero `[Phase 3]`
_Report §4 + §8 bracket column._

- Gusset variants: flat L, triangular gusset, double-gusset, ribbed. Compare under one load
  ("3 mm gusset cuts tip deflection 72% for +18 g; control moves plate→bolt tension").
- Implement the real bolt model (retire the `bolt_group_loads` stub): **separate** shear,
  tension, bearing-in-plate, tear-out / edge-distance warning, washer/contact option,
  wall-substrate warning, explicit **"does not check wall anchorage"** disclaimer.
- **Tests:** `test_bracket` gains gusset-deflection and bolt-bearing/tear-out oracle cases.

### Milestone G — Evidence: case studies + report export `[Phase 5]`
_Report §11–13._

- Two more case studies to join the existing one: **robot-arm link** (stiffness controls
  before stress) and **mini-crane compression member** (buckling showcase). Reuse the
  Milestone-D review output as each case's narrative.
- PDF/CSV/JSON export (problem → assumptions → load cases → candidates → failure-mode table
  → plots → limitations → validation). Use the `pdf` skill for the report.
- Optional: one **physical test** (3D-print a bracket, load known weights, measure
  deflection, document prediction-vs-measured + error sources). A *failed* test documented
  well is still strong evidence per §13.

### Milestone H — Optional depth (only if time) `[stretch]`
- Uncertainty/Monte Carlo mode (§6), load-case envelopes (§7), units IO layer (§15),
  section-editor teaching overlays (§9: neutral axis, I-contribution, "material far from NA
  is efficient"). Each is self-contained and additive.

---

## 3. Explicitly NOT doing (report §17)

Full 3D FEA from scratch · AI chatbot · large unsourced material DB · dozens of exotic
sections · UI animation for its own sake · any code-compliance / structural-approval claim ·
topology optimization (unless tightly scoped to gusset suggestions later). Asymmetric
sections (T/L/channel) from the old roadmap are **deferred** — not in this review's path.

---

## 4. Ground rules carried over

1. **Oracle-first testing.** Every new numeric target is hand-derived from the governing
   equation and printed for spot-check. **Fix the code, never edit a verified test target.**
2. **Honesty as a feature.** Unmodeled effects appear as active warnings, not buried
   disclaimers (§14). "Not modeled" is a valid, visible status.
3. **Backward compatibility.** The Milestone-A refactor must keep the existing 117 tests
   green; the duplication collapse is invisible to current callers.
4. **Verify locally.** Sandbox has no PyPI — confirm with `cd mechopt && pytest -q` before
   committing, then commit + push (the pending CSS/README items in `PROJECT_CONTEXT §6`
   should go out first so the live app is current).

---

## 5. Suggested first commit boundary

`Milestone A` alone is a clean, low-risk PR: a pure refactor + new `failure_modes.py` + new
tests, with zero behavior change on existing outputs. It unlocks B, C, D, and the future
shear/torsion checks. **Recommended starting point when you greenlight building.**

---

## 6. Public-facing pitch (report §20, adopt once core ships)

> A transparent structural design-space explorer for early-stage mechanical design. It
> evaluates beams and wall-mounted brackets across materials, sections, dimensions, stock
> constraints, and failure modes, then explains the best tradeoffs using stress, deflection,
> buckling, bolt-group analysis, cost, mass, sensitivity, and validation evidence.
