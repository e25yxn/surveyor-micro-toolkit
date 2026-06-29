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
