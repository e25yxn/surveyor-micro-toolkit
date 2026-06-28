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
