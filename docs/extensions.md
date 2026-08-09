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
**Commit:** `454b55d`
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

---

## Oracle Correction — build_alignment_from_pi Curve-Overlap Direction Guard

**วันที่:** 2026-08-05
**Commit:** `39df582`
**ไฟล์:** `src/smt/builders/alignment_builder.py`, `src/smt/optimizer.py`
**Tests:** `tests/builders/test_alignment_builder.py` class `TestCurveOverlapDetection`
(7 เคสใหม่: `test_overlapping_curves_report_issue`,
`test_overlapping_curves_geometry_unchanged`,
`test_non_overlapping_close_curves_no_issue`,
`test_barely_non_overlapping_curve_small_positive_margin`,
`test_inside_tolerance_no_issue_but_overlap_flag_set`,
`test_past_tolerance_still_reports_issue`, `test_bp_as_prev_label`),
`tests/test_optimizer.py::TestRealData::test_gap_improves_and_r_stable`
(regression กลับมา PASS หลังแก้ coupling)
**อ้างอิง:** `session_logs/review_src_smt_20260802.md` #2,
`session_logs/plan_20260804_2014.md`,
`session_logs/tmp_verify_bug2_curve_overlap.py`,
`session_logs/tmp_verify_bug2_golden_pi_overlap.py`

### ประเภทงาน: Oracle correction exception (ไม่ใช่ Extension ปกติ)
เหมือนกับ entry "Singular Deflection Guard" ก่อนหน้า — งานนี้แก้ **defect จริง
ในตัวสมการที่พอร์ตมาจาก oracle เอง** ไม่ใช่ความสามารถใหม่ที่ oracle ไม่มี
จึงไม่ใช้เลข EXT-00X ต่อ ตามกฎ "Oracle correction exception" ใน CLAUDE.md

### Oracle limitation / defect ที่พบ
`build_alignment_from_pi` วางตำแหน่ง tangent element ระหว่างจุดจบของ PI/BP
ก่อนหน้า (`prev`) กับจุดเริ่มโค้งของ PI ปัจจุบัน (`curve_start` / TS/PC) ด้วย

```python
tan_len = wcb.calculate_distance_2d(prev_n, prev_e, curve_start_n, curve_start_e)
sta_cs  = prev_sta + tan_len
```

`calculate_distance_2d` เป็น `math.hypot(...)` — **ระยะทางไม่มีเครื่องหมาย
เสมอ** ดังนั้นถ้า PI สองตัวติดกันมี R/Ls ใหญ่จนโค้งซ้อนทับกัน (tangent ระหว่าง
กลางไม่พอ) `curve_start` จะอยู่**ข้างหลัง** `prev` จริง (ในพิกัด N/E) แต่
`tan_len` ที่คำนวณได้ยังเป็นบวกเสมอ → สร้าง tangent element ที่ "เดินหน้า"
ทั้งที่เรขาคณิตจริงพับกลับ → chain ขาดต่อกันแบบเงียบสนิท **ไม่มีรายการใน
`issues` เลย** จะเห็นบั๊กนี้ก็ต่อเมื่อผู้ใช้รัน check_chain เองแยกต่างหาก

ยืนยันแล้วว่า `reference/AlignmentBuilder.gs:123`
(`var tanLen = WCB.distance2D(prev.n, prev.e, curveStart.n, curveStart.e);`)
มีบั๊กเดียวกันเป๊ะ — `WCB.distance2D` (`reference/WCB.gs:41-43`) คือ
`Math.hypot(n2-n1, e2-e1)` ก็เป็น unsigned distance เหมือนกัน (พอร์ตมาจาก
ที่เดียวกัน)

**พิสูจน์ collinearity (ไม่ใช่การประมาณ):** `prev` และ `curve_start` อยู่บน
เส้น `azimuth_in` เดียวกันโดยโครงสร้างเสมอ ดังนั้น dot product
`(curve_start − prev) · (cos az_in, sin az_in)` คือระยะโปรเจกชันที่มี
เครื่องหมายจริง ไม่ใช่ค่าประมาณ — component ตั้งฉากเป็น 0 เสมอ
ยืนยันเชิงประจักษ์ด้วยเคส reproduce จริง
(`session_logs/tmp_verify_bug2_curve_overlap.py`,
BP(0,0)→PI1(200,0,R=500)→PI2(250,80,R=500)→EP(400,150)):
`abs(tan_len) == abs(tan_len_signed)` ตรงเป๊ะทั้งสองจุด —
**PI1 เทียบ BP: `tan_len_signed = −77.1240 m`**,
**PI2 เทียบ PI1: `tan_len_signed = −330.7850 m`** — ทั้งคู่ติดลบ คือโค้งซ้อน
ทับกันจริงทั้งสองจุด ไม่ใช่แค่จุดเดียว (พบระหว่างเขียนสคริปต์ reproduce เอง)

### ประวัติ threshold A → B
1. **เริ่มด้วย A** (ตามแผน `plan_20260804_2014.md` หัวข้อ 1): raw
   `tan_len_signed < 0`, ไม่มี tolerance ใดๆ — เหตุผลตอนนั้นคือ "ตรงรายงานเป๊ะ
   ไม่เดาค่าคงที่ใหม่ที่ไม่มีหลักฐาน" (หลีกเลี่ยงปัญหาเดียวกับ finding #17 ใน
   review, ค่า tolerance ที่กระจัดกระจายไม่มีที่มา)
2. รันจริงกับ `test_data/AL1_test_alignment_PI.csv` (ไฟล์จริงหลังแก้พิกัด
   PI7-PI11) เจอ **PI#7/PI#8: `tan_len_signed = −0.0005 m` (0.5mm)** —
   ติดลบจริงตาม threshold A แต่เป็น noise จากพิกัดที่ปัดทศนิยม 3 ตำแหน่งตาม
   ธรรมเนียมงานสำรวจ ไม่ใช่โค้งซ้อนทับกันจริงในแบบ
3. รันข้อมูลจริงชุดที่สอง `test_data/HOR_01N01.csv` เจอเพิ่ม
   **PI#1/BP: `−0.0013 m`**, **PI#7/PI#8: `−0.0016 m`** — ยืนยัน pattern
   เดียวกันซ้ำ (เกิดที่รอยต่อโค้งกลับทิศติดกันทั้งสองไฟล์) ไม่ใช่เหตุบังเอิญ
   ไฟล์เดียว
4. ตัดสินใจเปลี่ยนเป็น **B**: เพิ่ม `TOL_METERS = 0.02` (2 ซม.) เป็น module
   constant (`src/smt/builders/alignment_builder.py`) — ~12 เท่าเหนือ noise
   สูงสุดที่เจอจริง (−1.6mm) และยังต่ำกว่าโค้งซ้อนทับที่มีนัยสำคัญทางวิศวกรรม
   (ระดับเมตร) มาก พร้อม comment อ้างอิงที่มาของค่าไว้ในโค้ดโดยตรง
5. ข้อความ issue เปลี่ยนจาก `... ต้อง >= 0` เป็น
   `... ต้อง >= -{TOL_METERS:.2f} ม.` — เงื่อนไข trigger issue เปลี่ยนจาก
   `tan_len_signed < 0` เป็น `tan_len_signed < -TOL_METERS`

**สถานะยืนยันจริง (ไม่ใช่คาดการณ์):** รันไฟล์จริงทั้งสองไฟล์ตรงๆ ผ่าน
`build_alignment_from_pi` ที่แก้แล้ว — ทั้งคู่ได้ `issues == []` และ
`has_geometric_overlap == True` (ตรงกับที่ TOL_METERS ควรทำ: เงียบสำหรับ
noise ระดับ mm แต่ flag ภายในยังจับได้)

### ผลข้างเคียงที่พบและแก้: fit_radius (EXT-002) coupling
`optimizer.py::fit_radius` ใช้ `built.issues` (ไม่ว่าง = ไม่ผ่าน) เป็น hard
validity constraint ของ objective function มาก่อน **โดยไม่รู้ตัวว่ามี
coupling นี้อยู่** — เปลี่ยน threshold เป็น B แล้วรัน
`tests/test_optimizer.py::TestRealData::test_gap_improves_and_r_stable`
พังทันที: `ΔR` ที่เคยอยู่ต่ำกว่า 1m (เกณฑ์ test) กระโดดเป็น **18.6m** เพราะ
overlap ระดับ mm ที่เคยถูก `issues` (threshold A) กันไว้เป็น hard constraint
ตอนนี้ผ่านเงียบ (threshold B) ทำให้ optimizer เดินเข้าไปในพื้นที่ค้นหาที่มี
overlap จริงระดับ mm ได้อย่างอิสระ แล้วลู่เข้าคำตอบที่ R เปลี่ยนมากผิดปกติ

**วิธีแก้:** เพิ่ม field ใหม่ `BuildResult.has_geometric_overlap: bool` —
strict (zero-tolerance), ตั้งจาก `tan_len_signed < 0` ตรงๆ ไม่ผ่าน
`TOL_METERS` เลย แล้วเปลี่ยน `optimizer.py::fit_radius` ให้เช็ค
`built.issues or built.has_geometric_overlap` แทนเช็ค `built.issues` เดี่ยวๆ

**ทำไมต้องแยกสองสัญญาณนี้ออกจากกัน:**
`issues` คือ **สัญญาณสำหรับผู้ใช้** (human-facing warning) — ต้องทน noise
ระดับ mm จากพิกัดปัดเศษ ไม่งั้นผู้ใช้เจอ warning ที่ไม่มีความหมายทุกครั้งที่
เปิดไฟล์จริง (ตามประวัติ threshold A→B ข้างบน) ส่วน `has_geometric_overlap`
คือ **สัญญาณสำหรับ internal search constraint** — optimizer ต้องไม่เดินเข้า
พื้นที่ที่โค้งซ้อนทับกันจริงแม้แต่ mm เดียว เพราะ objective function
(sum of squared gaps) ไม่มีทางรู้ว่า geometry ที่ดู "gap น้อย" นั้นได้มาจาก
โค้งที่พับทับตัวเองในพิกัดจริง — ผสมสองสัญญาณนี้เป็นตัวเดียวจะบังคับให้เลือก
ระหว่าง "ผู้ใช้เจอ warning noise ทุกไฟล์" กับ "optimizer เดินเข้า overlap
จริงได้อย่างอิสระ" ซึ่งทั้งคู่ไม่ใช่พฤติกรรมที่ต้องการ

### Before/After

**(ก) threshold A → B บนเคส PI1/PI2 เดิม** (จาก
`tmp_verify_bug2_curve_overlap.py`) — overlap 77m/330m ใหญ่กว่า `TOL_METERS`
(2ซม.) มาก จึงไม่เปลี่ยนพฤติกรรมเลย:

| | threshold A | threshold B |
| --- | --- | --- |
| `issues` | 2 รายการ (PI#1 vs BP: −77.1240 m, PI#2 vs PI#1: −330.7850 m) | เหมือนเดิมทุกประการ — 2 รายการ ข้อความเปลี่ยนจาก "ต้อง >= 0" เป็น "ต้อง >= -0.02 ม." เท่านั้น |
| `has_geometric_overlap` | (field ยังไม่มีอยู่ในตอนนั้น) | `True` |
| `elements`/`control` | เหมือนเดิม (fallback = append-issue-only) | เหมือนเดิม ไม่เปลี่ยน |

**(ข) `has_geometric_overlap` บนเคส AL1 จริง**
(`test_data/AL1_test_alignment_PI.csv`, PI#7/PI#8 = −0.5mm) — ยืนยันจริงด้วย
`build_alignment_from_pi` รันตรงจากไฟล์:

| ค่า | ผลจริง |
| --- | --- |
| `issues` | `[]` (ว่างเปล่า — noise ระดับ mm ไม่ trigger threshold B) |
| `has_geometric_overlap` | `True` (strict flag ยังจับได้ — ใช้เป็น internal constraint ใน `fit_radius` ได้ต่อ) |

(ยืนยันซ้ำด้วย `test_data/HOR_01N01.csv` เช่นกัน — `issues == []`,
`has_geometric_overlap == True`)

### Regression guarantee
- `pytest tests/builders/test_alignment_builder.py -q` → **76 passed**
  (69 เดิม + 7 เคสใหม่ของ `TestCurveOverlapDetection`, รวม boundary เคส
  ข้าม/ไม่ข้าม `TOL_METERS`)
- `pytest -q` เต็มชุด → **514 passed**
- `pytest tests/test_optimizer.py::TestRealData::test_gap_improves_and_r_stable -v`
  → **PASSED** (กลับมาผ่านหลังแก้ coupling ด้วย `has_geometric_overlap` —
  ยืนยันแล้วว่าไฟล์ `ramp01n01_SO.csv`/`r01n01_so_crosscheck.csv` มีอยู่จริง
  ทำให้ test นี้รันจริง ไม่ได้ถูก skip)

### สถานะ .gs/VBA — divergence ที่รู้ตัว ยังไม่ sync
- **`reference/AlignmentBuilder.gs:122-123`** — ยืนยันแล้วว่ามีบั๊กเดียวกัน
  เป๊ะ (unsigned distance ล้วนๆ, ไม่มี `tan_len_signed`/`TOL_METERS`/
  `has_geometric_overlap` เลย) — **ยังไม่แก้ตามในรอบนี้** — known divergence
  ตาม Oracle correction exception ข้อ 5 งาน sync เป็นงานแยกต่างหาก ไม่ปิดจน
  กว่าจะ sync เสร็จ
- **`reference/AlignmentBuilder.gs:145`** (`endLen` — EP-tangent สุดท้ายจาก
  exit ของโค้งสุดท้ายไปยัง EP) ก็ใช้ `WCB.distance2D` แบบ unsigned เหมือนกัน
  ตรงกับ Python `alignment_builder.py` (`ep_len`) — **ตรวจสอบเพิ่มเติมแล้วว่า
  ไม่ใช่บั๊ก (#2b, 2026-08-05):** ยืนยันด้วยการทดสอบว่า kink (มุมหักที่จุดต่อ
  EP) เท่ากับ `0.000000000°` ในทุกเคสที่ทดสอบ — ประเด็นนี้ปิดแล้ว ไม่ใช่
  known divergence ที่ต้องรอ sync
- **VBA (`reference/vba/`)** — `build_alignment_from_pi`/`buildFromPI` ไม่มี
  VBA port เลย (ตาราง "VBA Engine map" ใน CLAUDE.md ไม่มี AlignmentBuilder.gs
  อยู่) — ไม่มีโค้ด VBA ที่ต้องพิจารณา divergence สำหรับบั๊กนี้

## Oracle Correction — parse_pi_table Orphan Compound-Sub-Row Guard

**วันที่:** 2026-08-07
**Commit:** `795f36b`
**ไฟล์:** `src/smt/builders/alignment_builder.py`
**Tests:** `tests/builders/test_alignment_builder.py` class `TestParsePiTable`
(3 เคสใหม่: `test_orphan_compound_arc_before_first_pi_raises`,
`test_orphan_compound_arc_after_ep_raises`,
`test_orphan_compound_arc_multiline_reports_first_line`)
**อ้างอิง:** `session_logs/review_src_smt_20260802.md` #3,
`session_logs/plan_20260807_1904.md`

### ประเภทงาน: Oracle correction exception (ไม่ใช่ Extension ปกติ)
เหมือนกับ entry "Singular Deflection Guard" และ "Curve-Overlap Direction Guard"
ก่อนหน้า — งานนี้แก้ **defect จริงในตัวฟังก์ชันที่พอร์ตมาจาก oracle เอง**
ไม่ใช่ความสามารถใหม่ที่ oracle ไม่มี จึงไม่ใช้เลข EXT-00X ต่อ ตามกฎ
"Oracle correction exception" ใน CLAUDE.md

### Oracle limitation / defect ที่พบ
`parse_pi_table` เก็บ compound sub-row (แถวที่ POINT ว่างแต่ RADIUS มีค่า)
ไว้ในตัวแปร `compound_arcs` ระหว่างรอ flush เข้ากับ PI ที่กำลัง pending อยู่:

```python
def _flush_pending() -> None:
    nonlocal pending_pi
    if pending_pi is None:
        return
    if compound_arcs:
        ...
```

เมื่อ `_flush_pending()` ถูกเรียกตอน `pending_pi is None` (คือยังไม่เจอ PI
ใดๆ เลย หรืออยู่หลัง EP ที่ไม่ set pending_pi) ฟังก์ชัน `return` ทันทีโดย
**ไม่เคลียร์ `compound_arcs`** — ทำให้ arc ที่ค้างอยู่:
1. รั่วไปเกาะ PI ตัวถัดไปที่ไม่เกี่ยวข้อง (ถ้า orphan sub-row อยู่ก่อน PI
   ตัวแรก) กลายเป็น compound curve ผิดตัวแบบเงียบ
2. หายไปเงียบๆ โดยไม่มี error ใดๆ (ถ้า orphan sub-row อยู่หลัง EP)

ยืนยันแล้วว่า `reference/gsheet/GS_PiTableParser.gs` มีบั๊กเดียวกันเป๊ะ —
`flushPending_()` มี `if (pendingPi === null) return;` เหมือนกันบรรทัดต่อ
บรรทัด (พอร์ตแบบ mirror ตรงๆ) ยืนยันด้วยการรันสถานการณ์เดียวกันผ่าน Node
จริงกับไฟล์ `.gs` นี้ตรงๆ ได้ผลลัพธ์ตรงกัน

VBA (`reference/vba/`) ไม่มีพอร์ต `parse_pi_table` เลย (เหมือนกรณี #2
`build_alignment_from_pi`) — ไม่มีโค้ด VBA ที่ต้องพิจารณา divergence สำหรับ
บั๊กนี้

### ขอบเขต
เฉพาะ orphan sub-row ก่อน PI ตัวแรก / หลัง EP เท่านั้น — กรณี sub-row แทรก
กลางหลัง PI ที่มี compound arc ถูกต้องอยู่แล้วไม่เข้าข่ายบั๊กนี้ เพราะแยกไม่
ออกจากโค้ง compound หลายส่วนที่ตั้งใจจริงในฟอร์แมต ถือเป็นความกำกวมของ
ฟอร์แมตเอง ไม่ใช่บั๊ก parsing

### วิธีแก้
เพิ่มตัวแปร `compound_arcs_first_line: int = 0` เก็บเลขบรรทัดของ arc ตัวแรก
ในแต่ละกลุ่ม แล้วใน `_flush_pending()` ก่อน `return` เดิมตอน
`pending_pi is None` ให้เช็ค `if compound_arcs:` — ถ้ามี arc ค้างอยู่ raise
`ValueError` ระบุเลขบรรทัดของ arc ตัวแรกที่พบปัญหา แทนที่จะปล่อยผ่านเงียบๆ
จุดแก้เดียวใน `_flush_pending()` ครอบคลุมทั้งสองสถานการณ์ (ก่อน PI ตัวแรก /
หลัง EP) เพราะฟังก์ชันนี้ถูกเรียกทั้งกลางลูป (ก่อนแถวชื่อถัดไป) และท้ายไฟล์
เหมือนกัน

### Before/After

**ตัวอย่าง 1 — orphan sub-row ก่อน PI ตัวแรก:**
```
POINT,N,E,STA,R,LS,DELTA
,,,,150,,10
BP,0,0,0,,,
PI1,100,100,,300,,
```

| | เดิม | ใหม่ |
| --- | --- | --- |
| ผลลัพธ์ | `compound_arcs=[{R:150,delta:10}]` ค้างจาก orphan แล้วไปรวมกับ arc ของ PI1 แบบผิดๆ | `raise ValueError` ทันทีที่เจอ BP: "compound sub-row (แถวที่ 2) มีค่า RADIUS แต่ไม่มี PI ก่อนหน้าให้ผูก ..." |
| error | ไม่มี | มี ระบุเลขบรรทัดชัดเจน |

**ตัวอย่าง 2 — orphan sub-row หลัง EP:**
```
POINT,N,E,STA,R,LS,DELTA
BP,0,0,0,,,
PI1,100,100,,300,,
EP,200,200,,,,
,,,,150,,10
```

| | เดิม | ใหม่ |
| --- | --- | --- |
| ผลลัพธ์ | คืน vertices 3 ตัว (BP,PI1,EP) เฉยๆ ข้อมูล R=150 หายไปเงียบๆ | `raise ValueError` ตอน `_flush_pending()` เรียกครั้งสุดท้าย: "compound sub-row (แถวที่ 5) มีค่า RADIUS แต่ไม่มี PI ก่อนหน้าให้ผูก ..." |

**ตัวอย่าง 3 — control, format ถูกต้อง (ไม่พังทั้งเดิมและใหม่):**
```
POINT,N,E,STA,R,LS,DELTA
BP,0,0,0,,,
PI1,100,100,,,,
,,,,300,,15
,,,,150,,
EP,200,200,,,,
```

เหมือนกันทุกประการทั้งก่อน/หลังแก้ — PI1 ได้ `compound=[{R:300,delta:15},{R:150}]`
ไม่มี error เพราะ `pending_pi` ไม่ใช่ `None` ตอน flush ในกรณีนี้ (ยืนยันด้วย
เทสเดิมที่มีอยู่แล้ว `test_compound`/`test_pi_radius_zero_with_compound_still_works`
ไม่ต้องเพิ่มเทสซ้ำ)

### Regression guarantee
- `pytest tests/builders/test_alignment_builder.py::TestParsePiTable -v` →
  **16 passed** (13 เดิม + 3 เคสใหม่ของ orphan-arc guard)
- `pytest -q` เต็มชุด → **517 passed** (514 เดิม + 3 ใหม่)

### สถานะ .gs — divergence ที่รู้ตัว ยังไม่ sync
- **`reference/gsheet/GS_PiTableParser.gs`** — ยืนยันแล้วว่ามีบั๊กเดียวกันเป๊ะ
  (`flushPending_()` ไม่เคลียร์ `compoundArcs` ตอน `pendingPi === null`
  เหมือนกัน) — **ยังไม่แก้ตามในรอบนี้** — known divergence ตาม Oracle
  correction exception ข้อ 5 งาน sync เป็นงานแยกต่างหาก ไม่ปิดจนกว่าจะ sync
  เสร็จ
- **VBA (`reference/vba/`)** — ไม่มีพอร์ต `parse_pi_table` เลย — ไม่มีโค้ด
  VBA ที่ต้องพิจารณา divergence สำหรับบั๊กนี้

## Oracle Correction — check_against_drawing No-Match Reporting + Station-Distance Ceiling

**วันที่:** 2026-08-09
**Commit:** (ยังไม่ commit — จะเติมหลัง commit ตามแบบแผนเดิม)
**ไฟล์:** `src/smt/builders/alignment_builder.py`, `src/smt/builders/vertical_builder.py`
**Tests:** `tests/builders/test_alignment_builder.py` class `TestDefensiveBuilder`
(5 เคสใหม่), `tests/builders/test_vertical_builder.py` (`test_check_against_drawing_report_fields`
แก้ไข + class `TestDefensiveVerticalBuilder` 2 เคสใหม่)
**อ้างอิง:** `session_logs/review_src_smt_20260802.md` #4,
`session_logs/plan_20260809_check_against_drawing.md`

### ประเภทงาน: Oracle correction exception — เงื่อนไขข้อ (1) เป็น N/A

ต่างจาก entry ก่อนหน้า (#1/#2/#3) ที่พิสูจน์ว่า `.gs` มี defect เดียวกัน —
`check_against_drawing` **ไม่มีพอร์ตใน `reference/gsheet/` หรือ `reference/vba/`
เลยสักที่** ฟังก์ชันที่ `GS_CrossCheck.gs::checkPoints()` mirror จริงคือ
`check.py::check_horizontal()` (คนละฟังก์ชัน คนละอัลกอริทึม — คำนวณตำแหน่ง
ณ สถานีที่ drawing ระบุโดยตรง ไม่ค้นหาจุดใกล้สุด จึงไม่มีบั๊กนี้เลย) เงื่อนไข
ข้อ (1) ("พิสูจน์ว่า oracle มี defect เดียวกัน") จึงเป็น N/A ในความหมายที่
ปลอดภัยกว่าเดิม — ไม่มี oracle ให้ขัดตั้งแต่แรก จึงไม่มีความเสี่ยงขัดกับ
พฤติกรรมที่เคย verify ไว้ ยังต้องผ่านเงื่อนไขที่เหลือ (proof เชิงตรรกะ,
เทส, เอกสาร, tracking) เหมือนเดิม

### Oracle limitation / defect ที่พบ

`check_against_drawing` (ทั้งสองไฟล์) มี 2 จุดที่พฤติกรรมเดิมอันตราย:

1. drawing point ที่ชื่อไม่ match control point ใดเลย → `best is None` →
   `continue` **เงียบ ไม่มีแถวในรายงานเลย** — เครื่องมือ verify ที่ข้ามจุด
   ตรวจไม่ได้แบบเงียบอันตรายที่สุด เพราะรายงานที่เหลือดูผ่านหมด ผู้ใช้เข้าใจ
   ว่าตรวจครบ
2. การจับคู่ closest-by-station **ไม่มีเพดานระยะ** — จุดที่ห่างจาก control
   ที่ใกล้สุดเป็นร้อย/พันเมตร ก็ยังถูกจับคู่แล้วรายงาน FAIL ที่ชวนสับสน
   แทนที่จะบอกว่า "ไม่มีคู่"

รันจริงกับ `test_data/AL1_test_alignment_drawing.csv` (45 แถว) ก่อนแก้:
30 matched, 15 no-match — **ทั้ง 15 แถวหายไปเงียบๆ ไม่มีร่องรอยในรายงานเลย**

### ขอบเขต

แก้ 2 จุดในฟังก์ชันเดียวกัน ทำกับทั้ง 2 ไฟล์ (โครงสร้างเหมือนกัน):
1. แทนที่ `if best is None: continue` ด้วยการ append แถว no-match ที่มี
   schema เดียวกับแถวปกติทุกประการ (`note` เป็น key เสมอทุกแถว — ปกติ `''`,
   ไม่พบ/ไกลเกินเป็นข้อความอธิบาย) กัน `KeyError` ฝั่งโค้ดที่เอา report ไปใช้ต่อ
2. เพิ่มพารามิเตอร์ `max_sta_distance: float | None = 10.0` — ถ้าจุดใกล้สุด
   ยังห่างเกินนี้ ถือเป็น "ไม่พบ" เหมือนกัน (note ต่างข้อความ) แทนรายงาน FAIL
   ที่สับสน default 10.0m (ความคลาดเคลื่อนหน้างานจริงไม่เกินไม่กี่เมตร ระยะ
   ระหว่างจุดจริงในไฟล์อยู่หลักร้อย-พันเมตร — 10m แยกกรณีจริงจาก
   typo/ป้ายชื่อผิดที่ไปจับจุดไกลๆ ได้ชัดเจน) — `None` ปิดเพดานได้
   (คืนพฤติกรรมเดิม)

### Before/After

**ตัวอย่าง — orphan drawing point (ชื่อไม่ match):**
```
control = [ControlPoint('PC', sta=100, ...)]
drawing = [{'name':'PC',...}, {'name':'XYZ',...}]
```
| | เดิม | ใหม่ |
| --- | --- | --- |
| ผลลัพธ์ | `report` มีแค่ 1 แถว (PC) — XYZ หายไปเงียบๆ | `report` มี 2 แถว — XYZ ได้แถว `ok=False, note='ไม่พบจุดควบคุมที่ชื่อตรงกัน'` |

**ตัวอย่าง — จับคู่ไกลเกินไป:**
```
control = [ControlPoint('BP', sta=0), ControlPoint('EP', sta=600)]
drawing = [{'name':'','sta':300,...}]   # อยู่กึ่งกลาง ไม่ใกล้จุดไหนเลย
```
| | เดิม | ใหม่ (default 10m) |
| --- | --- | --- |
| ผลลัพธ์ | จับคู่กับ BP (ห่าง 300m) รายงาน `ok=False` เหมือน FAIL ธรรมดา | `ok=False, note='จุดควบคุมที่ใกล้สุด (BP) ห่างตามสถานี 300.000 ม. เกินเพดาน 10.000 ม.'` |

### Regression guarantee

- `pytest tests/builders/test_alignment_builder.py::TestDefensiveBuilder -v` →
  ผ่านหมด (2 เทสเดิมที่ assert พฤติกรรมบั๊กเดิมตรงๆ ถูกแทนที่ด้วยเวอร์ชันใหม่
  ที่ assert พฤติกรรมถูกต้อง + เพิ่ม 3 เคสใหม่สำหรับ `max_sta_distance`)
- `pytest tests/builders/test_vertical_builder.py -v -k check_against_drawing`
  → ผ่านหมด (โครงสร้างเดียวกัน)
- `pytest -q` เต็มชุด → **528 passed** (517 เดิม + สุทธิ 11 ใหม่)
- รันจริงกับ `AL1_test_alignment_drawing.csv` (ฉบับแก้ไขแล้ว): core fix
  อย่างเดียว (ไม่มี adapter) ยังคง 30 matched, 15 no-match **แต่ทุกแถวโผล่
  ในรายงานแล้ว** ไม่ใช่หายเงียบเหมือนก่อน

### สถานะ .gs/VBA — ไม่มี divergence ต้อง track

ไม่มีพอร์ตของ `check_against_drawing` ใน `reference/gsheet/` หรือ
`reference/vba/` เลย (ยืนยันด้วย `grep` ทั้ง repo ไม่เจอ) — ไม่มีโค้ด GAS/VBA
ที่ต้องพิจารณา divergence สำหรับ fix นี้เลย

---

## EXT-004 — check_against_drawing Naming Adapters (IP/PCC)

**วันที่:** 2026-08-09
**Commit:** (ยังไม่ commit — จะเติมหลัง commit ตามแบบแผนเดิม)
**ไฟล์:** `src/smt/check.py` (ฟังก์ชันใหม่ล้วนๆ ไม่แตะ protected function ใดๆ)
**Tests:** `tests/test_check.py` (6 เคสใหม่: `test_normalize_ip_names_*` ×3,
`test_add_pcc_control_points_*` ×3)
**อ้างอิง:** `session_logs/plan_20260809_check_against_drawing.md`

### ที่มา

ระหว่าง validate fix ด้านบนกับข้อมูลจริง (`AL1_test_alignment_drawing.csv`)
พบว่า 33% ของแถว (15/45) เป็น no-match — 11 แถว (`PI1`-`PI11`) ถูกต้องอยู่แล้ว
โดยธรรมชาติ (PI คือจุดตัดแทนเจนต์ ไม่ใช่จุดบนเส้นทางจริง ไม่ควรมี control
point ให้จับคู่) แต่ 4 แถว (`IP1`, `IP2`, `PCC`×2) มีจุดจริงตรงตำแหน่งเป๊ะใน
control แค่ชื่อไม่ตรง convention — CK1024 ยืนยันแล้วว่าอยากให้แจ้งเป็น "ไม่พบ"
ให้ผู้ใช้ไปตรวจสอบเอง (ไม่ใช่เดา/auto-fix) แต่กรณี IP/PCC นี้มีจุดจริงรออยู่
แค่ชื่อไม่ตรง สมควรแก้ที่ต้นตอของชื่อแทน

### ฟังก์ชัน

- **`normalize_ip_names(drawing)`** — ตัดเลขออกจากชื่อ `IP<เลข>` ทุก format
  (`IP1`/`IP-1`/`IP-01`/`IP-001`/`IP 1`) → `IP` เปล่า ให้ตรงกับชื่อที่ control
  ใช้จริง (control ตั้งชื่อจุดไม่มีโค้งเป็น `IP` เฉยๆ เสมอ ไม่มีเลข) ไม่แตะ
  `PI*` เลย (ถูกต้องอยู่แล้วที่ไม่ต้อง match) คืน list ใหม่ ไม่แก้ input เดิม
- **`add_pcc_control_points(control, sta_tolerance=0.01)`** — หา `PT` ตามด้วย
  `PC` ทันทีที่ station ห่างกัน ≤ `sta_tolerance` (default 1cm — ยืนยันจาก
  ข้อมูลจริง: 2 คู่ในไฟล์ AL1 ห่างกัน 0.0004-0.001m) แล้วสร้างจุด control
  สังเคราะห์ชื่อ `PCC` ที่ midpoint เพิ่มเข้า list คืน list ใหม่ ไม่แก้ input เดิม

### ทำไมไม่ใช่ Oracle correction

ฟังก์ชันใหม่ล้วนๆ ไม่แตะ `check_against_drawing`/`build_alignment_from_pi`
แม้แต่บรรทัดเดียว — เป็น adapter หน้า protected function ตรงตามกฎมาตรฐาน
ของโปรเจกต์ (`parse_pi_table`/`build_alignment_from_pi`/`check_against_drawing`
ต้องไม่ถูกแก้โดยตรง งานใหม่เป็น adapter แทน) ไม่เข้าเงื่อนไข Oracle correction
exception ใดๆ

### Regression guarantee + real-data validation

- `pytest tests/test_check.py -v` → 6 เคสใหม่ผ่านหมด (ครอบคลุม: ตัดเลขทุก
  format, ไม่แตะชื่ออื่นที่ไม่เกี่ยว, ไม่ mutate input ทั้งสองฟังก์ชัน, `PT`/`PC`
  ที่ห่างกันจริงไม่ถูกสร้าง `PCC` ปลอม)
- `pytest -q` เต็มชุด → **528 passed**
- รันจริงกับ `AL1_test_alignment_drawing.csv` ผ่านทั้ง adapter: **34 matched,
  11 no-match** (เพิ่มจาก 30/15) — เหลือแค่ `PI1`-`PI11` ที่ถูกต้องอยู่แล้ว
  gap ของ 4 จุดที่ match ได้ใหม่: 0.0-0.0008m (ยืนยันเป็นจุดเดียวกันจริง)
- ทดสอบ default `max_sta_distance=10.0` (จาก entry ด้านบน) ว่าไม่บล็อกจุด
  ที่ควร match จริงแม้แต่จุดเดียวในข้อมูลนี้
