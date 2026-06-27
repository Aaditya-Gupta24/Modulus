# MechOpt Test Loop

Use this loop whenever you want a new feature or result:

1. State the desired result in one sentence.
2. Add or update a test that proves the result, using hand-derived numbers for engineering calculations.
3. Run the loop and read the first failure.
4. Fix implementation code only.
5. Rerun until the suite is green.
6. Update docs or UI after the physics/core behavior is protected by tests.

The tests are the oracle. Do not loosen, skip, delete, or rewrite verified numeric targets just to make a failure disappear.

## One-Shot Run

From `C:\Users\AADITYA GUPTA\OneDrive\Desktop\MechOpt\mechopt`:

```powershell
.\scripts\test-loop.ps1
```

This runs:

```powershell
uv run --with-requirements requirements.txt pytest -q
```

The script sets `UV_CACHE_DIR` to the repo-local `.uv-cache` so it does not depend on a global cache path.

## Watch Mode

```powershell
.\scripts\test-loop.ps1 -Watch
```

Watch mode reruns whenever source or test files change. Keep it open while editing; stop it with `Ctrl+C`.

## Target A Smaller Slice

```powershell
.\scripts\test-loop.ps1 -PytestArgs @("tests/test_sections.py", "-q")
.\scripts\test-loop.ps1 -PytestArgs @("tests/test_optimizer.py::test_safest_is_max_fos_among_safe", "-q")
```

## Agent Prompt

When asking an agent to drive the loop, use this:

```text
Desired result: <one clear behavior or feature>.

Work test-first. Add/adjust tests for the desired result using independently derived expected values where engineering math is involved. Then run .\scripts\test-loop.ps1 from the mechopt project root. Read the first failing assertion, fix implementation code only, and repeat until all tests pass. Do not weaken verified numeric targets, skip tests, or change public signatures unless absolutely necessary.
```

## Good Next Loops

- Move beyond screening by adding Euler buckling with known-answer tests.
- Add neutral-axis/parallel-axis tests for asymmetric T and L sections.
- Add JS-vs-Python parity checks for the standalone `index.html` dashboard.
- Add input validation tests for non-positive loads, lengths, and material dimensions.
- Add a simple benchmark or case-study notebook after the core equations are locked.
