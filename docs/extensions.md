# SMT Extensions Beyond Oracle

This file records every feature that goes beyond the validated Google Apps Script oracle
(`reference/*.gs`). Each entry states: what the oracle could not do, what we added,
the mathematical basis, and where to find the code and tests.

---

## EXT-001 — No-Curve PI (Angle Point) Support

**Commit:** `cdf896d`
**Module:** `src/smt/builders/alignment_builder.py`
**Test class:** `TestNoCurvePI` (12 cases)

### Oracle limitation
The Apps Script oracle silently produced `NaN` (or skipped the segment) whenever a PI
entry carried no radius information. There was no way to represent an **angle point** —
a PI where two tangent runs meet with a deflection but no circular curve inserted.

### What we added
`alignment_builder.py` now accepts a PI record as an **angle point** when any of the
following conditions is detected:

| Condition | Interpretation |
|-----------|---------------|
| `R` field absent / `None` | radius not supplied → angle point |
| `R = 0` | explicit zero radius → angle point |
| Three consecutive points are collinear | deflection = 0 → trivial angle point |

When an angle point is detected the builder emits a control point with name `'IP'`
(Intersection Point), zero arc length, and the station carried forward unchanged.
The two adjoining tangent segments connect directly at this point.

### Mathematical basis
An angle point is the degenerate case of a circular curve where `R → ∞` (equivalently
`k = 1/R → 0`). The two tangent directions meet at the PI with a finite deflection
angle `Δ`, but no arc is interpolated. This is standard highway geometry practice for
low-speed or temporary alignments and for re-entrant geometry where a curve is
intentionally omitted.

Reference: *AASHTO A Policy on Geometric Design of Highways and Streets* (Green Book),
definition of Intersection Angle / Deflection Angle at a PI without a curve.

### Code markers
All code paths and tests added for this extension are marked with the comment:

```python
# EXTENSION: beyond oracle
```

### Tests (12 cases in `TestNoCurvePI`)
| # | Scenario |
|---|----------|
| 1 | R = None — angle point created |
| 2 | R = 0 — angle point created |
| 3 | Collinear PIs — trivial angle point |
| 4 | Angle point station equals PI station (no arc advance) |
| 5 | Control point name is `'IP'` |
| 6 | Mixed: curve PI followed by angle-point PI |
| 7 | Mixed: angle-point PI followed by curve PI |
| 8 | Two consecutive angle points |
| 9 | Alignment with only angle points (no curves) |
| 10 | Downstream stations remain correct after angle point |
| 11 | Azimuth propagates correctly through angle point |
| 12 | Round-trip: station → coordinates consistent through angle point |

### Regression guarantee
All 250 pre-existing oracle tests continue to pass (verified in commit `cdf896d`).
Angle-point paths are additive; no existing public signature was changed.

---

## EXT-003 — COSINE Transition: Civil 3D Sine Half-Wave Closed Form

**Date:** 2026-07-05
**Commits:** `301245c`, `db39b85`, `162ef98`, `aa8038c`, `ce75e4a`, `214db4e` (see
`session_logs/latest.md` for the full commit-by-commit breakdown), plus the
`_build_curve_sub_elements` fix and second fixture regeneration committed alongside
this doc entry.
**Modules:** `src/smt/alignment.py`, `src/smt/builders/alignment_builder.py`
**Tests:** `tests/test_alignment.py` (`test_cosine_closed_form_endpoint_r900_l100`,
`test_cosine_closed_form_endpoint_r250_l50`, `test_cosine_spin_spout_symmetry_matches_civil3d`)
plus the full suite

### Oracle limitation
`reference/Alignment.gs` and `reference/AlignmentBuilder.gs` model the COSINE transition
shape as a curvature-vs-arc-length integral (`f(τ)=(1-cos πτ)/2`), the same mechanism as
CLOTHOID/BLOSS/SINE. This does not match real Autodesk Civil 3D COSINE spirals ("Sine
Half-Wavelength Diminishing Tangent Curve"), which are defined by a closed-form y(x) in
tangent-projected distance, not arc length — verified independently against 2 Civil 3D
ground-truth points. Comparing the old formula's tanLong/tanShort against the verified
closed-form values: **~2.90cm off at R=900/L=100**, **~4.71cm off at R=250/L=50**.
Because `AlignmentBuilder.gs` also sizes a PI-group's circular arc assuming every
spiral's total turning angle equals `Ls/(2R)` (exact for the Simpson-based shapes, since
`∫₀¹f=1/2` always), fixing only the point-position formula left a second, smaller
(~34 arcsecond) inconsistency at the circular-arc-sizing level.

### What we added
1. `alignment.py::calculate_point_on_element` — new closed-form COSINE branch (SPIN
   direct, SPOUT mirrored via s↔L−s), replacing Simpson integration for this shape only.
   See `session_logs/plan_cosine_sinehalfwave_fix.md`,
   `session_logs/investigate_sinehalfwave_formula.md`.
2. `alignment_builder.py::_build_curve_sub_elements` — real spiral turning angle via a
   synthetic SPIN element + `calculate_exit_state`, replacing the `Ls/(2R)` assumption.
   See `session_logs/investigate_cosine_builder_mismatch_20260705.md`,
   `session_logs/investigate_build_curve_sub_elements_fix.md`.
3. `tests/golden/tables.json` + `reference/tables.json` regenerated twice (once per
   change above) so the shared golden fixture reflects both fixes.

### Mathematical basis
- COSINE closed form: `X = L - 0.0226689447*L³/R²`,
  `y(x) = X²/R·(a²/4 - (1-cos πa)/(2π²))`, `theta(x) = atan(X/R·(a/2 - sin(πa)/(2π)))`,
  `a=x/X`. Source: Autodesk Civil 3D 2026 Help, "About Transition Definitions".
- SPOUT mirror: `theta_SPOUT(d) = Θ − theta_SPIN(L−d)`, position via reflect+rotate —
  confirmed against real Civil 3D data that SPIN/SPOUT of equal R,L share identical
  theta/totalX/totalY/tanLong/tanShort.
- Builder fix: the real turning angle Θ replaces `Ls/(2R)`; proven identical to the old
  formula for CLOTHOID/BLOSS/SINE (diffs ~1e-16, float noise, checked across 6
  R/Ls/trans combinations) since those three satisfy `F(1)=1/2` exactly — only COSINE's
  Θ genuinely differs (`atan(X/(2R)) ≠ L/(2R)`).

### Code markers
```python
# EXTENSION: beyond oracle — reference/AlignmentBuilder.gs (lines 53-54) still
# assumes theta=Ls/(2R); real turning angle needed for the COSINE closed form.
```

### Known limitations (unresolved, documented in full in alignment.py's docstring)
- `x≈s` (tangent-projected distance approximated by arc length) costs ~1.5-4.5mm at the
  element's own exit; no interior point is independently verified at all.
- The SPOUT mid-curve trace is derived from the boundary mirror only — no independent
  Civil 3D ground truth confirms any SPOUT interior point.
- LandXML's `totalX` field reports `L`, not the true closed-form `X`.

### Regression guarantee
CLOTHOID/BLOSS/SINE are numerically unaffected by either change — proven, not assumed
(see Q3 in `session_logs/investigate_build_curve_sub_elements_fix.md` for the builder
fix, and the unchanged golden-fixture rows outside the COSINE PI-group for the
closed-form fix). Confirmed: `pytest -q` → `457 passed, 0 xfailed, 0 failed` — fully
green, both xfail marks removed, no regression anywhere in the suite.

---

## EXT-002 — Radius Optimisation (fit_radius)

**วันที่:** 2026-06-29
**Commit:** ececeaa (optimizer.py) + ecb9496 (smt fit-radius CLI)
**ไฟล์:** `src/smt/optimizer.py`, `src/smt/cli.py`
**Tests:** `tests/test_optimizer.py` (9 cases)

### Oracle ทำอะไรไม่ได้

Oracle (`reference/AlignmentBuilder.gs`) รับ R ที่กำหนดมาแล้วคำนวณ alignment ให้เท่านั้น
ไม่มีความสามารถในการหาค่า R ที่ทำให้ alignment ตรงกับแบบมากที่สุด

### สิ่งที่เพิ่ม

`fit_radius(pi_rows, drawing_points, fix_names, tol, max_iter)` — ใช้ scipy Nelder-Mead
หาค่า R ของแต่ละ PI ที่ทำให้ sum of squared gaps ระหว่างจุดที่คำนวณได้กับจุดจากแบบน้อยที่สุด

**หลักการทางคณิตศาสตร์:**
- Objective function: Σ[(N_calc - N_draw)² + (E_calc - E_draw)²] สำหรับจุด PC/PT/BP/EP
- Method: Nelder-Mead (gradient-free, robust กับ function ที่ไม่ smooth)
- Sign convention: เก็บ sign ของ R แยก optimize เฉพาะ abs(R) เพื่อไม่ให้ flip ทิศทางเลี้ยว
- Bounds: R ≥ 1.0m เสมอ (ป้องกัน R → 0)
- Penalty: 1e6 per point เมื่อ build มี issues หรือ station อยู่นอก alignment

### ผลการทดสอบ (ramp01n01_SO.csv)

| | ก่อน optimize | หลัง optimize |
|---|---|---|
| gap รวม | 14.7mm | 1.2mm |
| max gap จุดเดียว | ~7.4mm | 0.73mm |
| iterations | — | 289 |
| converged | — | True |

R ที่ได้เปลี่ยนน้อยมาก (ΔR < 0.1m บน R=150m) ยืนยันว่า gap เดิมมาจาก rounding
ของทศนิยม 3 ตำแหน่งในแบบ ไม่ใช่ error จริงในการออกแบบ

### CLI

```
smt fit-radius <pi_csv> <drawing_csv> [--fix PI1,PI2] [--tol 1e-6] [--max-iter 10000]
```

### ข้อควรระวัง

- ต้องติดตั้ง scipy ก่อน: `pip install -e ".[optimize]"`
- ถ้าแบบให้ค่า 3 ทศนิยม: optimizer จะได้ R ที่ "แปลก" เล็กน้อย (เช่น 149.905 แทน 150)
  เพราะ compensate rounding — ใช้ R กลมๆ เดิมก็เพียงพอสำหรับงานส่วนใหญ่
- IP (angle point, R=0) ถูก skip อัตโนมัติ ไม่ optimize
