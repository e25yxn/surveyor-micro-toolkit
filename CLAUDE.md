# SMT (Surveyor Micro Toolkit) - context for Claude Code

GOAL: a pure, typed, tested Python **core engine** for road / highway / ramp alignment
math. This is the single source of truth from which CLI, API, Excel, notebooks, and
interop (LandXML/CSV/DXF) will derive. It is also a teaching reference.

## Principles (non-negotiable)
SAFE - SMALL - STABLE - MODULAR.

## Coding rules
- Pure functions in the core: no I/O, no global state, no side effects.
- NO rounding inside the core. Round/format only at the display/output boundary.
- Angles in **radians** internally; degrees / packed-DMS only at boundaries.
- Sign conventions: offset `+`=right of travel, `-`=left; radius `+`=right, `-`=left;
  tangent R=0; curvature `k = 1/R` (signed).
- Type hints on every function; dataclasses / NamedTuple for records.
- Docstrings state: what it does + units + sign convention + reference formula.
- Keep functions small (one job). Don't add numpy/abstractions without a failing test.

## Naming (full guide: docs/naming_convention.md)
- Anatomy (all languages): name = [verb Action] + [Target] + [Context],
  e.g. calculate_northing_from_azimuth. Context may be dropped if obvious.
- Casing (Python core): snake_case for functions/methods/variables; PascalCase for
  classes; UPPER_SNAKE_CASE for constants. (JS/VBA mirror uses camelCase for funcs/vars.)
- Approved verbs (one per concept, use consistently): calculate_ (math), get_ (lookup),
  make_ (one object), build_ (assemble many), parse_ (table->struct), normalize_,
  round_/trunc_, check_ (cross-check), is_/has_/in_ (boolean).
  Unit conversion uses the idiom <source>_to_<target> (deg_to_rad).
- Ubiquitous language: use survey terms (alignment, station, offset, azimuth/WCB,
  curvature, radius, tangent, spiral, transition, vertical_curve, grade, crossfall,
  PI, VPI, PC, PT, control_point, deviation, profile).
- Allowed abbreviations ONLY: N, E, sta, R, k, PI, VPI, PC, PT, SC, CS, TS, ST, WCB,
  LVC, dms. Spell out everything else (azimuth not az, distance not dist).
- 4 senior rules: clarity > brevity; one verb per concept; speak the expert's language;
  don't repeat the class/module name inside a method.

## Oracle + testing (how we guarantee correctness)
- `reference/*.gs` is the validated engine (passed AllTests 45/45). **Python MUST match it.**
- `reference/tables.json` and `tests/golden/tables.json` hold known-answer fixtures
  (30-element alignment, 31 control points, vertical table, cross-fall).
- Workflow: **TDD, bottom-up**. Write/keep golden tests, then make them green.
  Module order: fpmath -> wcb -> alignment -> vertical -> crossfall -> surface
  -> builders -> check.
- Always add a roundtrip test where it applies (forward->inverse recovers input).
- Run `pytest` (or `python dev_run_tests.py` if pytest is not installed yet).
- Don't change public signatures of passing modules; add, don't break.

## Module map (.gs -> .py)
## Status
Core engine complete: 250/250 tests passing across 7 commits. Next steps are
extension work (CLI, notebooks, LandXML I/O) — see docs/blueprint.md.

## Module map (.gs -> .py)
| reference (.gs)      | src/smt (.py)                  | status |
|-----------------------|--------------------------------|--------|
| FPMath.gs             | fpmath.py                      | [DONE] |
| WCB.gs                | wcb.py                         | [DONE] |
| Alignment.gs          | alignment.py                   | [DONE] |
| Vertical.gs           | vertical.py                    | [DONE] |
| CrossFall.gs          | crossfall.py                   | [DONE] |
| Surface3D.gs          | surface.py                     | [DONE] |
| AlignmentBuilder.gs   | builders/alignment_builder.py  | [DONE] |
| VerticalBuilder.gs    | builders/vertical_builder.py   | [DONE] |
| HorCheck.gs/VerCheck.gs | check.py                     | [DONE] |

## Known limits (carry over + document)
- spiral + compound combination unsupported.
- inverse exactly at a spiral-start node is a benign edge case (matches the JS oracle).
