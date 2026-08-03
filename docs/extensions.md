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

### GAS (Google Apps Script) mirror
`reference/gsheet/GS_Alignment.gs` + `reference/gsheet/GS_AlignmentBuilder.gs` port the same
COSINE closed-form + arc-length inversion + builder turning-angle fix to Google Apps Script,
mirroring the VBA port (`reference/vba/SMT_Alignment.bas`, commit `e285fd5`). Verified
2026-07-13: Node smoke-test (23/23) and Node-vs-Python diff=0 across 3 R/L/trans points.
Beyond that, three vertex groups were checked — **Group A** (9 `GS_COSINE_*` UDF values)
and **Group B** (COSINE PI-vertex through `buildFromPI`) were confirmed by typing the
formulas into real Google Sheets cells; **Group C** (CLOTHOID through `buildFromPI`, same
vertex as Group B) was confirmed only via a local Node-vs-Python comparison (diff=0 on all
6 control points) — it has not yet been typed into a real Sheets cell. See
`session_logs/plan_20260713_0257.md`, `session_logs/latest.md`.

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

---

## Oracle Correction — build_alignment_from_pi Singular Deflection Guard

**วันที่:** 2026-08-02
**Commit:** `TBD` (เติมหลัง commit จริง)
**ไฟล์:** `src/smt/builders/alignment_builder.py`
**Tests:** `tests/builders/test_alignment_builder.py` class `TestNoCurvePI`
(3 เคสใหม่: `test_collinear_pi_with_radius_no_error`,
`test_reversal_pi_180deg_no_blowup`, `test_near_collinear_small_delta_still_solves`)
**อ้างอิง:** `session_logs/review_src_smt_20260802.md` #1,
`session_logs/plan_20260802_1904.md` + addendum

### ประเภทงาน: Oracle correction exception (ไม่ใช่ Extension ปกติ)
ต่างจาก EXT-001/002/003 ที่เป็นความสามารถใหม่ที่ oracle ไม่มี งานนี้แก้ **defect
จริงในตัวสมการที่พอร์ตมาจาก oracle เอง** (สันนิษฐานว่า `reference/AlignmentBuilder.gs`
มีการหารแบบเดียวกันไม่มี guard เพราะพอร์ตมาตรงๆ — ยังไม่ได้ตรวจ/แก้ไฟล์ .gs จริง
ดูหัวข้อ "สถานะ .gs/VBA" ด้านล่าง) จึงไม่ใช้เลข EXT-00X ต่อ ตามกฎ "Oracle
correction exception" ใน CLAUDE.md (เพิ่มเข้าไปพร้อมกันในรอบนี้)

### Oracle limitation / defect ที่พบ
`build_alignment_from_pi` แก้สมการ 2×2 หาจุดเริ่มโค้ง (TS/PC) ด้วย
`d1 = (V.n·sin(az_out) − V.e·cos(az_out)) / sin(δ)` โดย **ไม่มี guard ใดๆ** ต่อ
`sin(δ)` ที่เข้าใกล้ 0 — เกิดได้ 2 จุดเสมอ (δ ถูก normalize มาอยู่ใน `(−π, π]`
แล้วจาก `calculate_angle_diff`):

1. **δ≈0** (สามจุดเรียงเส้นตรงพอดี แต่ PI ยังระบุ R มาด้วย) → `ZeroDivisionError`
   ดิบทันที (Python หาร 0.0/0.0 ตรงๆ ไม่ raise เป็น NaN แบบภาษาอื่น)
2. **δ≈π** (มุมเบี่ยงหักกลับเกือบ 180°) → **ไม่ crash แต่เงียบสนิท** — geometry
   ที่ได้ผิดมหาศาล (พิสูจน์จริงด้วย geometry ตัวอย่าง: station พุ่งไปเกือบ 4
   พันล้านเมตร โดยไม่มี issue หรือ warning ใดๆ เลย) — อันตรายกว่ากรณีแรกมาก
   เพราะผู้ใช้ไม่มีทางรู้ตัวว่า output ผิด

### พิสูจน์ทางคณิตศาสตร์ (Extension policy ข้อ 3)
เขียน `v_n, v_e` (end-displacement ของกลุ่มโค้งวงกลม) ในเทอมของ δ ได้
`v_n = R sin(δ)`, `v_e = R(1−cos δ)` (สูตร chord มาตรฐาน) แทนใน d1:
```
d1 = R·sin(az_out) − R·[(1−cos δ)/sin δ]·cos(az_out)
```

**δ→0 (removable singularity):** `(1−cos δ)/sin δ → δ/2 → 0` ดังนั้น
`d1 → R·sin(az_out)` — ค่าจำกัดเสมอทางคณิตศาสตร์ แต่ Python หาร 0.0/0.0 ตรงๆ
ไม่ take limit ให้ — crash เฉพาะที่ δ เท่ากับ 0.0 ตรงเป๊ะ (float exact) ค่าใกล้ 0
เพียงเล็กน้อย (δ~10⁻⁸) ยังคำนวณได้ปกติสมบูรณ์ (พิสูจน์จริงด้วย regression test)

**δ→π (non-removable singularity):** ให้ `x = π−δ` (`x→0`), Taylor expansion
รอบ π ให้ `d1 ≈ R·sin(az_out) − 2R·cos(az_out)/x` — พจน์ `1/x` พุ่งไม่จำกัดจริง
**นี่คือ singularity เดียวกับสูตรมาตรฐานของ tangent length โค้งวงกลม**
`T = R·tan(Δ/2)` ซึ่ง `tan(π/2)` ไม่นิยาม — อ้างอิงเดียวกับ EXT-001
(*AASHTO A Policy on Geometric Design of Highways and Streets*, Green Book)
โค้งที่มุมเบี่ยง 180° ไม่มีอยู่จริงในงานวิศวกรรมถนน (hairpin แคบสุดในภูเขาก็ยัง
ต่ำกว่ามาก) — ไม่มีทางแก้สมการนี้ให้ได้ค่าที่สมเหตุสมผล

### สิ่งที่แก้
เพิ่ม guard ด้วย **2 เงื่อนไขอิสระ** (ไม่ใช่เงื่อนไขเดียว — ดูเหตุผลด้านล่าง)
ก่อนถึงจุดหาร ถ้า trigger จะข้ามไปใช้เส้นทาง angle-point (tangent-tangent, ตั้งชื่อ
control point ว่า `'IP'`) ที่มีอยู่แล้วจาก EXT-001 แทน พร้อม log คำเตือนใน
`issues` (ไม่เงียบเหมือนเดิม):

```python
if subs and (
    abs(math.sin(delta)) < fpmath.EPS                      # δ≈0
    or abs(math.pi - abs(delta)) < _NEAR_PI_EPS             # δ≈π
):
```

**ทำไมต้องแยก 2 เงื่อนไข ไม่ใช้ threshold เดียวร่วมกัน:** ลองแบบ threshold เดียว
(`abs(sin(delta)) < fpmath.EPS`, EPS=1e-9) ครอบทั้งสองกรณีก่อน — ผ่าน regression
test ของ δ≈0 (Case A/B) แต่ **ไม่ผ่าน** δ≈π (Case C จริง): `sin(δ)` ของ geometry
ตัวอย่างที่ทำให้ station พุ่งเป็นพันล้านมีค่าจริง **1.9999999890696914×10⁻⁷**
ใหญ่กว่า `fpmath.EPS`=1×10⁻⁹ ถึง ~200 เท่า — threshold แคบเกินไปสำหรับฝั่งนี้
เพราะ `abs(sin(delta))` เป็นค่าเดียวที่แยกไม่ออกว่า δ ใกล้ 0 หรือใกล้ π (ทั้งคู่ทำ
ให้ sin เข้าใกล้ 0 เหมือนกัน) ทั้งที่สอง singularity มี "รัศมีอันตราย" ต่างกันมาก
ตามพิสูจน์ข้างต้น (removable vs non-removable) — ต้องวัด δ≈π ด้วยระยะห่างจาก π
โดยตรง (`abs(math.pi - abs(delta))`) แยกเป็นเงื่อนไขที่สอง

### ที่มาของ `_NEAR_PI_EPS = 1×10⁻⁴`
ไม่ใช่ค่าที่เดาขึ้นมา — มาจาก noise floor จริงในงานสำรวจที่ CK1024 ยืนยันด้วย
ไฟล์ Civil 3D ของตัวเอง: พิกัด input จากแบบปัดทศนิยม 3 ตำแหน่งตามธรรมเนียมงาน
สำรวจ ทำให้เกิด rounding noise สะสมทั่วระบบ — เมื่อขยายทศนิยมพิกัดเป็น 15 ตำแหน่ง
แล้วเช็คคู่จุด BP-PC ที่ควรเป็นจุดเดียวกันทางทฤษฎี พบว่าห่างกันจริง ~1×10⁻⁷ เมตร
ทุกครั้งที่เช็ค (ไม่ใช่ครั้งเดียว) — นี่คือ noise floor จริงของระบบ

`_NEAR_PI_EPS = 1×10⁻⁴` (~20 arcsec จาก π พอดี) อยู่เหนือ noise floor นี้ ~1,000
เท่า (กันไม่ให้ noise ธรรมดาทำให้ curve จริงถูกเบี่ยงไป angle-point โดยไม่ตั้งใจ)
และยังห่างจากมุมเบี่ยงของ hairpin โค้งจริงที่แคบที่สุดในงานวิศวกรรมถนน
(~170-175°, เทียบเท่า ~0.087-0.17 rad จาก π) มาก — จึงไม่มีทางกิน design โค้งจริง
ใดๆ เข้าไปในเส้นทาง angle-point โดยไม่ตั้งใจ ขณะที่ยังกว้างพอจับเคสจริงที่พบ
(x≈2×10⁻⁷) ได้สบายๆ (ห่างจาก threshold ~500 เท่า)

`fpmath.EPS` (1×10⁻⁹, generic — ไม่มีจุดประสงค์เฉพาะเจาะจงในโค้ดเบสก่อนหน้านี้)
ยังใช้ร่วมสำหรับฝั่ง δ≈0 ตามเดิม เพราะ removable singularity ไม่ต้องการ
threshold กว้าง — `_NEAR_PI_EPS` ประกาศแยกเป็นค่าคงที่ใหม่เฉพาะฝั่ง δ≈π เท่านั้น

### Regression guarantee
`pytest tests/builders/test_alignment_builder.py -v` → **69 passed** (66 เดิม +
3 เคสใหม่: δ=0 พอดี มี R ระบุ, δ≈π มี R ระบุ, δ ใกล้ 0 มากแต่ไม่ trigger guard —
ยืนยันว่า threshold ไม่กว้างเกินจนกิน legit curve) — `pytest -q` เต็มชุดยังไม่รัน
ในขั้นตอนนี้ (รอตรวจก่อน commit)

### สถานะ .gs/VBA — divergence ที่รู้ตัว ยังไม่ sync
`reference/AlignmentBuilder.gs` และ `reference/vba/SMT_Alignment.bas` **ยังไม่ถูก
แก้ตาม** — สันนิษฐานว่ามี division เดียวกันแบบไม่มี guard (พอร์ตมาจากที่เดียวกัน)
แต่ยังไม่ได้ตรวจสอบ/ยืนยันจริง ถือเป็น known divergence ตามกฎ Oracle correction
exception ข้อ 5 — งาน sync เป็นงานแยกต่างหาก ไม่ปิดจนกว่าจะ sync เสร็จ
