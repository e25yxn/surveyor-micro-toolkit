# Session Log

## [2026-07-02] Streamlit web UI (app.py) — 5 tabs, revision 2 ของแผน

- ทำ: implement ตามแผนที่อนุมัติแล้ว (`session_logs/plan_streamlit_ui_20260701_1400.md`, revision 2):
  - สร้าง `src/smt/webhelpers.py` — 4 pure helper functions (`read_csv_rows`,
    `parse_field_points`, `parse_drawing_points`, `parse_element_rows`) ไม่ import
    streamlit เลย, mirror `cli.py`'s private helpers ตรงๆ (รวมถึง `disc` default = `''`
    ไม่ใช่ `0.0` ตามจุดที่แก้ในแผน)
  - สร้าง `app.py` (root) — Streamlit UI 5 tabs (Build, Cross-Check, Compare Drawing,
    Fit Radius, Export LandXML) import helper จาก `smt.webhelpers`
  - Fit Radius verification table + Compare Drawing table มี column `status` แยก
    (`OK`/`OUTSIDE_ALIGNMENT`/`HIP`) ไม่ปนกับตัวเลขใน `calc_N/calc_E/gap_m` แล้ว
  - เพิ่ม `tests/test_app_helpers.py` (8 tests) import ตรงจาก `smt.webhelpers`
  - แก้ `pyproject.toml` — เพิ่ม `[project.optional-dependencies] ui = ["streamlit>=1.30", "pandas>=1.5"]`
    (เพิ่ม pandas เพราะ `app.py` ใช้ `DataFrame.to_csv()` ตามที่แผนระบุไว้ — streamlit เองก็ต้องพึ่ง pandas อยู่แล้ว)
- คำสั่ง: `pytest tests/test_app_helpers.py -q` → `pytest -q` → smoke test จริงด้วย
  `streamlit run app.py --server.headless=true --server.port=8765` + `curl localhost:8765`
  → ทดสอบ `webhelpers.parse_element_rows` กับไฟล์จริง `test_data/build_out/elements_output.csv`
- ผล: PASS — helper tests 8/8, full suite 452/452, smoke test HTTP 200 ไม่มี error ใน log,
  ไฟล์จริง parse ได้ 31 elements ถูกต้อง
- commit: df7d8fd
- หมายเหตุ: ยังไม่ push — รอคำสั่งผู้ใช้

## [2026-07-01] สลับ mapping SINE/COSINE ใน _spiral_lx_type

- ทำ: แก้ `src/smt/landxml.py` — `_SPIRAL_TYPE`: SINE→sinusoid (เดิม sineHalfWave), COSINE→sineHalfWave
  (เดิม sinusoid) CLOTHOID→clothoid และ BLOSS→bloss เหมือนเดิม
  - เพิ่ม test ใหม่ `test_spiral_lx_type_mapping` ใน `tests/test_landxml.py` ตรวจ mapping ทั้ง 4 ตัวตรงๆ
    (ของเดิมไม่มี test คุม SINE/COSINE โดยตรง)
- คำสั่ง: `pytest -q` → `smt export-landxml test_data/SettingOutTest.csv --name SettingOutTest --out test_data/SettingOutTest.xml`
- ผล: PASS 444/444 — smoke test: ตรวจ SettingOutTest.xml พบ PI4 (COSINE) → spiType="sineHalfWave",
  PI5 (SINE) → spiType="sinusoid" ตรงกับ mapping ใหม่
- commit: 5e98645

---

## [2026-07-01] เปลี่ยนวิธีคำนวณ totalX/totalY/tanLong/tanShort เป็นแบบ canonical (ไม่ขึ้นกับทิศทางจริง)

- ทำ: แก้ `src/smt/landxml.py`
  - ลบวิธีคำนวณเดิมที่ใช้พิกัด start/end จริง (`_spiral_geometry` แบบเดิมที่หมุนพิกัดจริงเข้า local frame) ทิ้งทั้งหมด
  - เขียน `_spiral_geometry(R, length, transition, theta_rad)` ใหม่: สร้าง synthetic `Element`
    ที่ n=0, e=0, azimuth=0, sta_start=0, sta_end=length, k_in=0, k_out=1/R (R คือรัศมีจำกัดเสมอ
    ไม่ว่า SPIN หรือ SPOUT), transition เดียวกับของจริง แล้วเรียก `calculate_point_on_element`
    ที่ distance=length ได้ local_n, local_e → totalX=local_n, totalY=local_e (บวกทั้งคู่)
    theta_rad ใช้ค่าเดียวกับที่คำนวณไว้แล้วสำหรับ attribute theta
    tanLong = totalX - totalY/tan(theta_rad), tanShort = totalY/sin(theta_rad)
  - import `calculate_point_on_element` เพิ่มจาก `.alignment`
  - Curve element ไม่แตะเลย
  - อัปเดต docstring
  - แก้ `tests/test_landxml.py`: `test_spout_geometry_attributes` เดิม (เทียบค่าจาก SPOUT พิกัดจริง)
    ใช้ไม่ได้แล้วเพราะตอนนี้ SPIN/SPOUT ที่ R และ length เท่ากันต้องได้ค่าเดียวกัน (canonical)
    → แทนที่ด้วย `test_spout_geometry_matches_spin` (เทียบ SPIN==SPOUT) และเพิ่ม
    `test_geometry_attributes_are_positive` (ตรวจ totalX, totalY > 0 ทุก Spiral)
- คำสั่ง: `pytest -q` → `smt export-landxml test_data/SettingOutTest.csv --name SettingOutTest --out test_data/SettingOutTest.xml`
- ผล: PASS 443/443 — smoke test: ตรวจ SettingOutTest.xml พบ SPIN/SPOUT คู่เดียวกัน (R, length เท่ากัน)
  ได้ totalX/totalY/tanLong/tanShort เท่ากันทุกคู่ ค่าทั้งหมดเป็นบวก, Curve ไม่เปลี่ยนแปลง
- commit: 3715369

---

## [2026-07-01] เพิ่ม totalX/totalY/tanLong/tanShort ใน Spiral element ทุกตัว

- ทำ: แก้ `src/smt/landxml.py`
  - เพิ่ม helper `_spiral_geometry(start_n, start_e, end_n, end_e, entry_azimuth_rad, theta_rad)`
    คำนวณ dN/dE → totalX, totalY (หมุนเข้า local frame ตาม entry azimuth) → tanLong, tanShort
    ตามสูตรที่กำหนด (tanLong = totalX - totalY/tan(theta), tanShort = totalY/sin(theta))
  - refactor `_theta_deg` → `_theta_rad` (คืนค่า radian แทน แล้วแปลงเป็นองศาตอนใส่ attribute theta)
    เพื่อให้ theta_rad ใช้ร่วมกับ _spiral_geometry ได้โดยไม่คำนวณซ้ำ
  - เพิ่ม attributes `totalX`, `totalY`, `tanLong`, `tanShort` (เมตร, ทศนิยม 6 ตำแหน่ง) ในทุก Spiral
    (SPIN และ SPOUT) รักษา rot, radiusStart, radiusEnd, spiType, length, theta ไว้เหมือนเดิม
  - Curve element ไม่แตะเลย
  - อัปเดต docstring
  - เพิ่ม test ใหม่ใน `tests/test_landxml.py`: `test_spin_geometry_attributes`, `test_spout_geometry_attributes`
    (ตรวจค่าตัวเลขจริงจาก fixture spiral symmetric R=400 Ls=60)
- คำสั่ง: `pytest -q` → `smt export-landxml test_data/SettingOutTest.csv --name SettingOutTest --out test_data/SettingOutTest.xml`
- ผล: PASS 442/442 — smoke test: ตรวจ SettingOutTest.xml พบ Spiral ทุกตัวมี totalX/totalY/tanLong/tanShort ครบ, Curve ยังคงเดิมไม่เปลี่ยนแปลง
- commit: acb56cd

---

## [2026-07-01] ลบ dirStart/dirEnd ออกจาก Spiral, เพิ่ม theta แทน (Curve ไม่แตะ)

- ทำ: แก้ `src/smt/landxml.py` ส่วนสร้าง Spiral (SPIN และ SPOUT)
  - ลบ `dirStart`/`dirEnd` ออกทั้งหมดจาก Spiral (Civil 3D ไม่ใช้ attribute นี้กับ Spiral)
  - เพิ่ม attribute `theta` = มุมเลี้ยวรวมของ spiral (องศา, ค่าสัมบูรณ์) คำนวณจาก
    `theta_deg = abs(rad_to_deg(calculate_angle_diff(exit_azimuth, entry_azimuth)))`
    โดยเพิ่ม helper `_theta_deg` ใหม่
  - Curve ยังคงมี `dirStart`/`dirEnd` เหมือนเดิม ไม่แตะ
  - attribute อื่นของ Spiral (rot, radiusStart, radiusEnd, spiType, length) คงเดิม
  - อัปเดต docstring
  - แก้ `tests/test_landxml.py`: เอา `test_spin_dir_start`/`test_spin_dir_end` ออก แทนที่ด้วย
    `test_spiral_no_dir_start`, `test_spiral_no_dir_end`, `test_spin_theta`, `test_spout_theta`
    (คาดค่า theta ≈ 4.297183° จาก 0.5 * k_out * L)
- คำสั่ง: `pytest -q` → `smt export-landxml test_data/SettingOutTest.csv --name SettingOutTest --out test_data/SettingOutTest.xml`
- ผล: PASS 440/440 — smoke test: ตรวจ SettingOutTest.xml พบ Spiral มี theta ทุกตัว ไม่มี dirStart/dirEnd หลงเหลือ, Curve ยังมี dirStart/dirEnd ครบ
- commit: 47e38b9

---

## [2026-07-01] ลบ attribute "type" ออกจาก Spiral, ใช้ "spiType" ใส่รูปร่าง spiral แทน toCurve/fromCurve

- ทำ: แก้ `src/smt/landxml.py` ส่วนสร้าง Spiral (SPIN และ SPOUT)
  - ลบ attribute `type=_spiral_lx_type(...)` ออกทั้งหมด
  - เปลี่ยน `spiType='toCurve'`/`spiType='fromCurve'` → `spiType=_spiral_lx_type(el.transition)` (ใส่ค่ารูปร่าง clothoid/bloss/sinusoid/sineHalfWave แทน)
  - attribute อื่น (rot, radiusStart, radiusEnd, length, dirStart, dirEnd) คงเดิมทั้งหมด
  - อ้างอิงจาก py-1.xml (Civil 3D 2023 export จริง) ที่ Spiral มีแค่ length, radiusEnd, radiusStart, rot, spiType — ไม่มี type, ไม่มี toCurve/fromCurve
  - อัปเดต docstring ให้ตรงกับ format ใหม่
  - แก้ `tests/test_landxml.py`: เปลี่ยนตัวเลือก spin/spout จาก `spiType=='toCurve'` เป็น `radiusStart=='INF'`; ลบ `test_spin_spi_type`/`test_spout_spi_type`/`test_spiral_type_clothoid` แทนที่ด้วย `test_no_type_attribute`, `test_spi_type_holds_shape`, `test_no_to_from_curve_values`
- คำสั่ง: `pytest -q` → `smt export-landxml test_data/SettingOutTest.csv --name SettingOutTest --out test_data/SettingOutTest.xml`
- ผล: PASS 438/438 — smoke test: ตรวจ SettingOutTest.xml พบ Spiral มี spiType="clothoid"/"bloss"/"sinusoid" ไม่มี type attribute ไม่มี toCurve/fromCurve เหลืออยู่เลย
- commit: 37b4bdf

---

## [2026-07-01] แก้ _rotation ให้คืน "cw"/"ccw" แทน "right"/"left"

- ทำ: แก้ `src/smt/landxml.py` ฟังก์ชัน `_rotation` — คืน `"cw"` เมื่อ k>0, `"ccw"` เมื่อ k<0
  (อ้างอิงจากไฟล์ py-1.xml ที่ Civil 3D 2023 export จริง ใช้ rot="cw"/"ccw" เท่านั้น ไม่เคยใช้ "right"/"left")
  - อัปเดต module docstring และ function docstring ให้ตรงกับค่าใหม่
  - แก้ `tests/test_landxml.py`: `test_rotation_right` → `test_rotation_cw` (assert `'cw'`), `test_left_turn_rotation` assert `'ccw'` แทน `'left'`
- คำสั่ง: `pytest -q` → `smt export-landxml test_data/SettingOutTest.csv --name SettingOutTest --out test_data/SettingOutTest.xml` → `smt export-landxml test_data/ramp01n01_SO.csv --name ramp_test --out test_data/mainline_test.xml`
- ผล: PASS 438/438 — smoke test: ทั้งสองไฟล์ export สำเร็จ, ตรวจ mainline_test.xml พบ rot="cw"/"ccw" เท่านั้น ไม่มี "right"/"left" หลงเหลือ
- commit: d743e31

---

## [2026-07-01] แก้ spiral type mapping + dirStart/dirEnd Civil 3D convention + คืน dirEnd

- ทำ: แก้ `src/smt/landxml.py` 3 จุดตามแผนที่อนุมัติ
  1. `_spiral_lx_type`: CLOTHOID→clothoid, BLOSS→bloss, SINE→sineHalfWave, COSINE→sinusoid (ตรงกับ Civil 3D จริง แทนที่จะ map ทุกอย่างเป็น clothoid)
  2. เพิ่ม `_to_civil_dir(az_rad)` แปลง SMT survey azimuth (radian, 0=North clockwise) → Civil 3D dir (decimal degrees, 0=East counterclockwise) ด้วย `(450 - deg) mod 360`; ใช้แทน `rad_to_deg` ตรงๆ ทุกจุดที่เขียน dirStart
  3. เพิ่ม `dirEnd` กลับเข้า Curve/Spiral ทุกตัว โดยใช้ `_to_civil_dir` กับ exit azimuth (เพิ่ม helper `_exit_azimuth`)
  - `_rotation` ตรวจแล้วคืน "right"/"left" (ไม่ใช่ "cw"/"ccw") — ของเดิมถูกอยู่แล้วตาม test ที่ผ่าน จึงไม่แก้
  - อัปเดต `tests/test_landxml.py`: `test_curve_dir_start` (คาด 0.0 แทน 90.0 ตาม civil convention), เพิ่ม `test_curve_dir_end` (คาด 270.0), `test_spin_dir_start` (คาด 0.0), เพิ่ม `test_spin_dir_end` (คาดว่า dirEnd ไม่ใช่ None)
- คำสั่ง: `pytest -q` → `smt export-landxml test_data/SettingOutTest.csv --name SettingOutTest --out test_data/SettingOutTest.xml` → `smt export-landxml test_data/ramp01n01_SO.csv --name ramp_test --out test_data/mainline_test.xml`
- ผล: PASS 438/438 — smoke test: ทั้งสองไฟล์ export สำเร็จ, ตรวจ XML พบ dirStart/dirEnd ต่อเนื่องกันระหว่าง element ถัดไป และ spiral type ตรงกับ BLOSS/COSINE/SINE ที่ใช้จริงใน ramp01n01_SO.csv
- commit: 4bc4f09

---

## [2026-07-01] ลบ dirEnd ออกจาก Curve และ Spiral ใน LandXML export

- ทำ: ลบ `dirEnd` attribute ออกจาก Curve, SPIN, SPOUT ทุกตัวใน `src/smt/landxml.py`
  - ลบ `_exit_azimuth_deg` helper (กลายเป็น dead code)
  - อัปเดต module docstring และ function docstring
  - แก้ `tests/test_landxml.py`: เปลี่ยน `test_curve_dir_end` → `test_curve_no_dir_end` (assert `dirEnd is None`) และ `test_spin_dir_end_is_float` → `test_spin_no_dir_end`
- คำสั่ง: `pytest -q` → `smt export-landxml test_data/SettingOutTest.csv --name SettingOutTest --out test_data/SettingOutTest.xml`
- ผล: PASS 438/438 — smoke test: XML regenerated ปกติ
- commit: 1280fb0

---

## [2026-07-01] Map BLOSS/COSINE/SINE spiral types to clothoid in LandXML export

- ทำ: แก้ `_SPIRAL_TYPE` dict ใน `src/smt/landxml.py` — ลบ BLOSS/COSINE/SINE ออก (ทั้ง 3 ตัว fall through เป็น 'clothoid' via default ใน `.get(..., 'clothoid')` อยู่แล้ว)
- คำสั่ง: `pytest -q` → `smt export-landxml test_data/SettingOutTest.csv --name SettingOutTest --out test_data/SettingOutTest.xml`
- ผล: PASS 438/438 (ไม่มี regression) — smoke test: XML regenerated ปกติ
- commit: abc2e7c

---

## [2026-06-30] LandXML 1.2 export — landxml.py + CLI + 27 tests

- ทำ: สร้าง LandXML 1.2 export feature ครบ 3 ไฟล์
  - `src/smt/landxml.py`: pure function `export_alignment_landxml(build_result, name)` — T→`<Line>`, C→`<Curve>` + Center, SPIN→`<Spiral radiusStart="INF">`, SPOUT→`<Spiral radiusEnd="INF">`, rot="right"/"left" (Civil 3D 2023), transition types mapped ครบ (clothoid/bloss/cosineCurve/sineCurve)
  - `src/smt/cli.py`: เพิ่ม subcommand `smt export-landxml <pi.csv> [--name] [--out]`
  - `tests/test_landxml.py`: 27 tests — TestTangentOnly (7), TestSimpleCurve (7), TestSpiralIn (8), TestAnglePoint (5)
- คำสั่ง: `pytest tests/test_landxml.py -v`, `pytest -q`, `smt export-landxml test_data/SettingOutTest.csv --name SettingOutTest`
- ผล: PASS 27/27 (landxml), PASS 434/434 (full suite, ไม่มี regression)
- smoke test: XML ถูกต้องครบทุก element type รวม BLOSS/COSINE/SINE spirals และ angle points
- commit: f1f07d1

## [2026-06-30] เปลี่ยนชื่อ function ใน SMT_Geometry.bas + อัปเดต README

- ทำ: เปลี่ยนชื่อ 2 functions ใน `reference/vba/SMT_Geometry.bas` (ทุกที่: declaration, comment, expected values)
  - `SMT_GlobalToChn` → `SMT_GlobalToY`
  - `SMT_GlobalToOfs` → `SMT_GlobalToX`
- อัปเดต `reference/vba/README.md`: ชื่อ function ในตาราง reference และ example usage
- คำสั่ง: Edit tool replace_all=true × 4 → git commit -F
- ผล: commit รวมกับ notebooks/02_alignment_fitting.ipynb + alignment_fitting.png

## [2026-06-30] สร้าง notebooks/02_alignment_fitting.ipynb — alignment fitting visualisation

- ทำ: สร้าง Jupyter notebook 5 sections ใช้ข้อมูลจริง `test_data/ramp01n01_SO.csv` + `test_data/r01n01_so_crosscheck.csv`
  - Section 1 Setup: load PI CSV (pi_rows ไว้ส่ง optimizer), build alignment เริ่มต้น, load drawing points → active_pts (non-PI/HIP)
    Summary: 12 elements, 13 control pts, 15 drawing pts / 9 active
  - Section 2 Before Plot: helper functions (_compute_gaps, _trace_centreline, _plot_alignment)
    centreline สีน้ำเงิน, control pts สีน้ำเงิน, drawing pts X สีแดง, gap vectors ×100 สีแดง
  - Section 3 Optimizer: fit_radius(pi_rows, drawing_points) → 5 free PIs, 289 iters, converged
    gap_before → gap_after ลดลง
  - Section 4 After Plot: patch pi_rows ด้วย r_optimized → rebuild → plot เหมือน Section 2
    export PNG → notebooks/alignment_fitting.png (dpi=150)
  - Section 5 Table: pandas DataFrame Name/STA/gap_before/gap_after/improvement% พร้อม green bar
- tools: gen_notebook.py (nbformat) → nbconvert --execute --inplace → verified all cells pass, no errors
- คำสั่ง: python gen_notebook.py → jupyter nbconvert --execute → git add → git commit -F
- ผล: commit 215bc82 — 2 files, 588 insertions (02_alignment_fitting.ipynb + alignment_fitting.png)

## [2026-06-30] จัดโครงสร้าง reference/vba/ ใหม่ — 7 modules → 5 modules

- ทำ: รวมไฟล์ VBA ใน `reference/vba/` จาก 7 ไฟล์เป็น 5 ไฟล์
  - `SMT_Core.bas` ใหม่: รวม SMT_FPMath + SMT_WCB (FPMath ก่อน, WCB ตาม)
  - `SMT_Alignment.bas` ใหม่: เปลี่ยนชื่อจาก SMT_Align + ดูด SMT_WCBatSta มาจาก SMT_Rotation3D
  - `SMT_Geometry.bas` ใหม่: รวม SMT_LocalCoord + RotX/RotY/RotZ จาก SMT_Rotation3D
  - `SMT_Vertical.bas`, `SMT_Crossfall.bas` คงเดิม ไม่เปลี่ยน
  - ลบ: SMT_FPMath.bas, SMT_WCB.bas, SMT_Align.bas, SMT_LocalCoord.bas, SMT_Rotation3D.bas
  - อัปเดต Attribute VB_Name ทุกไฟล์ใหม่
  - เขียน README.md ใหม่ทั้งหมด: dependency diagram (ASCII) + function reference ครบ 5 modules
- คำสั่ง: Write tool (SMT_Core/Alignment/Geometry.bas + README) → Remove-Item → git add -u → git commit -F
- ผล: commit 8a15ee7 — 6 files changed, 379 insertions, 399 deletions
- โครงสร้างใหม่: SMT_Core → SMT_Alignment (dep Core), SMT_Vertical, SMT_Crossfall, SMT_Geometry (dep Core)

## [2026-06-30] สร้าง SMT_Rotation3D.bas — 3-D rotation + WCB at station

- ทำ: สร้าง `reference/vba/SMT_Rotation3D.bas` — 2 ส่วน
- ส่วน 1: SMT_RotX, SMT_RotY, SMT_RotZ (port จาก code อาจารย์, แก้ 4 จุด)
  - Fix1: Dim i As Long (เดิม Integer ล้น >32767)
  - Fix2: nRows As Long
  - Fix3: คืน array ใหม่ (เดิม ByRef แก้ต้นฉบับ)
  - Fix4: cosA/sinA คำนวณครั้งเดียวก่อน loop
  - Convention: right-hand rule CCW, angle in radians, pts 1-based n×3 Variant
- ส่วน 2: SMT_WCBatSta(sta, rng) — tangent WCB (degrees,[0,360)) ที่ station ใดๆ
  - T: theta=0 | C: theta=d/R | SPIN: d²/(2RL) | SPOUT: d/R-d²/(2RL)
  - คืน degrees เพื่อใช้กับ SMT_LocalToN/E ได้ทันที
- อัปเดต `reference/vba/README.md` เพิ่ม SMT_Rotation3D reference tables
- คำสั่ง: Write tool → git add → git commit -F
- ผล: commit fd36af5 — 2 files changed, 246 insertions
- Expected values:
  RotZ([1,0,0], pi/2) = [0,1,0] | SMT_WCBatSta(0, SMT_Elements) = 90.0

## [2026-06-30] สร้าง SMT_LocalCoord.bas — Local ↔ Global coordinate conversion

- ทำ: สร้าง `reference/vba/SMT_LocalCoord.bas` port และปรับปรุงจาก CHOStoNE/NEtoCHOS
  - `SMT_LocalToN(n0,e0,aziBEG,chn,ofs)` — Local→Northing
  - `SMT_LocalToE(n0,e0,aziBEG,chn,ofs)` — Local→Easting
  - `SMT_GlobalToChn(n0,e0,aziBEG,n,e)` — Global→Chainage
  - `SMT_GlobalToOfs(n0,e0,aziBEG,n,e)` — Global→Offset (+right/-left)
- Forward: DS=Sqr(chn²+ofs²); localAz=SMT_Atan2(ofs,chn); globalAz=NormalizeAngle(localAz+aziBEG_rad); N=n0+DS*Cos, E=e0+DS*Sin
- Inverse: Chn=dN*Cos(az)+dE*Sin(az); Ofs=-dN*Sin(az)+dE*Cos(az)
- Private SMT_Atan2 ซ้ำมาจาก SMT_WCB (VBA ไม่อนุญาต cross-module Private access)
- aziBEG รับเป็น degrees แปลง radians ทันทีใน entry point
- อัปเดต `reference/vba/README.md` เพิ่ม SMT_LocalCoord reference table
- คำสั่ง: Write tool (SMT_LocalCoord.bas + README) → git add → git commit -F
- ผล: commit e6ba7eb — 2 files changed, 213 insertions
- Expected values ท้ายไฟล์ (Origin=1000,2000 az=90°):
  LocalToN(100,0)=1000.0 | LocalToE(100,0)=2100.0 | LocalToN(0,50)=950.0
  GlobalToChn(1000,2100)=100.0 | GlobalToOfs(950,2000)=50.0

## [2026-06-30] สร้าง SMT_Crossfall.bas — VBA port of crossfall.py (crossfall/superelevation lookup)

- ทำ: สร้าง `reference/vba/SMT_Crossfall.bas` พอร์ต 2 public functions จาก `src/smt/crossfall.py`
  - `SMT_CrossfallLeft(sta, rng)`  — left crossfall (%) ที่ station sta
  - `SMT_CrossfallRight(sta, rng)` — right crossfall (%) ที่ station sta
- Named Range SMT_Crossfall: 6 คอลัมน์ (StaStart, StaEnd, CF_L_Start, CF_L_End, CF_R_Start, CF_R_End)
- Algorithm: linear interpolation ภายใน segment: CF = CF_Start + (CF_End-CF_Start)*(sta-StaStart)/(StaEnd-StaStart)
- Station range rule ตรง Python oracle: [StaStart,StaEnd) ยกเว้น last segment [StaStart,StaEnd]
- Sign: ลบ=ลาดออกจาก centerline (ระบายน้ำปกติ), บวก=ลาดเข้าหา centerline (superelevation)
- อัปเดต `reference/vba/README.md` เพิ่ม SMT_Crossfall reference table
- คำสั่ง: Write tool (SMT_Crossfall.bas + README) → git add → git commit -F
- ผล: commit c022258 — 2 files changed, 156 insertions
- Expected values (project dataset):
  sta=0→-2.0 | sta=530 Left→-1.0 (runout mid) | sta=700 Left→7.0 (full super) | sta=530 Right→-2.0

## [2026-06-30] สร้าง SMT_Vertical.bas — VBA port of vertical.py (elevation lookup)

- ทำ: สร้าง `reference/vba/SMT_Vertical.bas` พอร์ต 1 public function จาก `src/smt/vertical.py`
  - `SMT_Elevation(sta, rng)` — คำนวณ elevation ที่ station ใดๆ จาก Named Range SMT_Vertical (7 คอลัมน์)
- รองรับ 3 ประเภท segment:
  - LVC=0 → tangent grade: `Level + G1/100 * lx`
  - LVC>0, LVC2=0 → symmetric VC: `base + (G2-G1)/(200*LVC) * lx^2`
  - LVC>0, LVC2>0 → asymmetric VC: middle ordinate `e = L1*L2/(200*(L1+L2))*(G2-G1)`, arm1/arm2 formula
- Station range rule ตรง Python oracle: interior [StaStart,StaEnd), last [StaStart,StaEnd]
- อัปเดต `reference/vba/README.md` เพิ่ม SMT_Vertical reference table
- คำสั่ง: Write tool (SMT_Vertical.bas + README) → git add → git commit -F
- ผล: commit e77f438 — 2 files changed, 224 insertions
- Expected values (golden dataset):
  sta=0→100.0 | sta=1200→117.34375 | sta=2750→100.715075 | sta=2900→100.858475

## [2026-06-30] สร้าง SMT_Align.bas — VBA port of alignment.py (forward + inverse)

- ทำ: สร้าง `reference/vba/SMT_Align.bas` พอร์ต 4 public functions จาก `src/smt/alignment.py`
  - `SMT_StaToN(sta, offset, rng)` — Forward: sta+offset → Northing
  - `SMT_StaToE(sta, offset, rng)` — Forward: sta+offset → Easting
  - `SMT_CoordToSta(n, e, rng)`    — Inverse: N,E → station
  - `SMT_CoordToOffset(n, e, rng)` — Inverse: N,E → offset (+right/-left)
- Algorithm: Tangent=dot-product/straight-line; Circular=chord-half-angle/centre-of-curvature; Spiral=Simpson 48 steps (ทุก transition shape) + bisection inverse 50 รอบ
- อัปเดต `reference/vba/README.md` เพิ่ม SMT_Align function reference table
- คำสั่ง: Write tool (SMT_Align.bas + README) → git add → git commit -F
- ผล: commit 731bcc1 — 2 files changed, 540 insertions
- Expected values ท้ายไฟล์:
  SMT_StaToN(0,0,SMT_Elements)=1568000.0 | SMT_StaToE(519.615,0,SMT_Elements)=678519.615
  SMT_CoordToSta(1568000,678000,SMT_Elements)=0.0 | SMT_CoordToOffset(...)=0.0

## [2026-06-30] สร้าง SMT_WCB.bas — VBA port of wcb.py

- ทำ: สร้าง `reference/vba/SMT_WCB.bas` (VBA Module) พอร์ต 4 functions จาก `src/smt/wcb.py`
  1. `SMT_Azimuth(n1,e1,n2,e2)` — WCB azimuth rad [0,2π), guard coincident point
  2. `SMT_Distance(n1,e1,n2,e2)` — plan distance via Sqr(dN²+dE²)
  3. `SMT_CalcForward(n,e,az,dist,result)` — forward calc, result="N"/"E"
  4. `SMT_CalcOffset(n,e,az,dist,offset,result)` — forward + perpendicular offset
  - Private helper `SMT_Atan2(y,x)`: atan2 ครบ 5 quadrant cases (VBA ไม่มี built-in atan2)
  - Dependency: SMT_FPMath — เรียก `SMT_Pi()` และ `SMT_NormalizeAngle()` อย่าคำนวณซ้ำ
  - Expected values ท้ายไฟล์ตรงกับ Python golden data ทุกกรณี
- คำสั่ง: Write tool (ไม่มี test รัน — VBA module ต้องทดสอบใน Excel)
- ผล: ไฟล์สร้างสำเร็จ — ยังไม่ได้ commit

---

## [2026-06-30] สร้าง SMT_FPMath.bas — VBA port of fpmath.py

- ทำ: สร้าง `reference/vba/SMT_FPMath.bas` (VBA Module) พอร์ต 5 functions จาก `src/smt/fpmath.py`
  1. `SMT_Pi()` — คืนค่า π ด้วย `4 * Atn(1)` เต็ม Double precision
  2. `SMT_DegToRad(deg)` — degrees → radians
  3. `SMT_RadToDeg(rad)` — radians → degrees
  4. `SMT_NormalizeAngle(az)` — normalize rad ให้อยู่ใน [0, 2π)
  5. `SMT_AngleDiff(a, b)` — signed shortest diff (a-b) ใน (-π, π]
  - Private helper `SMT_FloorMod` ใช้ `Int()` แทน VBA `Mod` (ซึ่งแปลงเป็น Long ก่อน ทำให้ Double ผิด)
  - ท้ายไฟล์: expected values เทียบ Python golden data ครบ 8 กรณี
  - อัปเดต `reference/vba/README.md`: วิธี import .bas เข้า Excel, column mapping SMT_Elements, sign convention
- คำสั่ง: Write tool (ไม่มี test รัน — VBA module ต้องทดสอบใน Excel)
- ผล: ไฟล์สร้างสำเร็จ — ยังไม่ได้ commit
- หมายเหตุ: VBA Mod operator ทำงานกับ Integer/Long เท่านั้น ต้องใช้ `a - Int(a/n)*n` สำหรับ Double floor-mod

---

## [2026-06-29] smt fit-radius: เพิ่ม CLI subcommand เรียก optimizer

- ทำ: เพิ่ม `smt fit-radius` subcommand ใน `src/smt/cli.py` + 2 tests ใน `tests/test_cli.py`
  1. `_run_fit_radius(args)`: อ่าน PI CSV ด้วย `csv.reader` โดยตรง (raw rows), อ่าน drawing CSV ด้วย `_read_drawing_csv`, เรียก `fit_radius()`, แสดง R_initial vs R_optimized table + gap_before/gap_after + verification table (rebuild alignment ด้วย R optimised แล้วคำนวณ gap ทีละจุด)
  2. Parser: `smt fit-radius <alignment> <drawing> [--fix PI1,PI2] [--tol 1e-6] [--max-iter 10000]`
  3. `main()`: เพิ่ม `ImportError` ใน exception handler (สำหรับกรณี scipy ไม่ได้ติดตั้ง)
  4. Tests: `test_fit_radius_basic` (exit 0, 'gap_before'/'gap_after' ใน output), `test_fit_radius_missing_file` (exit 1)
- คำสั่ง: `pytest tests/test_cli.py -v`, `pytest -q`, `smt fit-radius test_data\ramp01n01_SO.csv test_data\r01n01_so_crosscheck.csv`
- ผล: PASS (407/407) — smoke test: gap_before=14.7mm → gap_after=1.2mm, 5 free PIs, 289 iters, converged=True, ทุก verification point < 0.75mm
- commit: ecb9496

---

## [2026-06-29 18:52] สร้าง optimizer.py — fit_radius (Nelder-Mead)

- ทำ: สร้าง `src/smt/optimizer.py` (EXTENSION: beyond oracle) และ `tests/test_optimizer.py` + เพิ่ม `optimize = ["scipy>=1.10"]` ใน `pyproject.toml`
  - `FitResult` dataclass: names, r_initial, r_optimized, gap_before, gap_after, n_points, iterations, converged, message
  - `fit_radius(pi_rows, drawing_points, fix_names, tol, max_iter)`:
    - หา free PIs จาก header (R≠0, ไม่อยู่ใน fix_names) เก็บ sign แยก optimize abs(R)
    - กรอง drawing points ออก PI*/HIP*
    - objective = Σgap² (penalty 1e6 ต่อจุดถ้า station นอก alignment หรือ build มี issues)
    - scipy Nelder-Mead + bounds=(1.0, None) per R
    - gap_before/after = √(Σgap²) หน่วยเมตร
  - แก้ geometry test ครั้งแรก (EP collinear → ZeroDivisionError) แล้วผ่าน
- คำสั่ง: `pytest tests/test_optimizer.py -v`, `pytest -q`, `mypy src/smt/optimizer.py`, `ruff check src/smt/optimizer.py`
- ผล: PASS (405/405) — mypy clean, ruff clean — real data test: gap_before≈7.4mm, gap_after≤gap_before, ΔR<1m

---

## [2026-06-29] smt compare-drawing: เพิ่ม subcommand เปรียบเทียบ drawing vs calculated

- ทำ: เพิ่ม CLI subcommand `smt compare-drawing` ใน `src/smt/cli.py`
  1. `_read_drawing_csv(path)`: อ่าน CSV header Name,STA,N,E → list of dict
  2. `_run_compare_drawing(args)`: สำหรับแต่ละ drawing point ถ้าชื่อขึ้นต้น PI หรือ HIP → แสดง HIP ไม่คำนวณ; ถ้าอื่น → คำนวณ delta_N, delta_E, gap_m (6 ทศนิยม), OK/FAIL vs --tol
  3. parser: รับ `elements` (elements CSV), `drawing` (drawing CSV), `--tol` default 0.010
  4. เพิ่ม `import math` ที่ top-level imports
- tests: เพิ่ม 3 cases ใน `tests/test_cli.py`
  - `test_compare_drawing_basic`: exit 0, ตรวจ BP/PI/HIP/CP1/OK ใน output
  - `test_compare_drawing_missing_file`: exit 1, 'error' ใน stderr
  - `test_compare_drawing_hip_no_crash`: HIP-only drawing → exit 0, 'HIP' ใน output
- คำสั่ง: `pytest -q`, `smt compare-drawing test_data\r01n01_elements_output.csv test_data\r01n01_so_crosscheck.csv`
- ผล: PASS (396/396) — smoke test ผ่านทุก row: gap_m ทุก point ≤ 0.010 m (max ~0.0074 m)
- commit: 3954047

---

## [2026-06-29] smt build: 6-decimal output, fix Transition column, add PI guard

- ทำ: แก้ `_run_build` ใน `src/smt/cli.py` 3 เรื่อง
  1. ทศนิยม 6 ตำแหน่ง: StaStart, StaEnd, N, E, Radius ใน `elements_output.csv`
     และ STA, N, E ใน `controls_so_output.csv` (เดิม 3 ตำแหน่ง)
  2. Transition column: T/C → ว่าง, SPIN/SPOUT → แสดงค่าจริง (เดิมแสดงค่า el.transition ทุก type)
  3. Guard: ถ้า `parse_pi_table` คืน `[]` → raise ValueError ภาษาไทย แทน IndexError traceback
- คำสั่ง: `pytest -q`, `smt build test_data\SettingOutTest.csv --out-dir test_data\build_out`
- ผล: PASS (393/393) — smoke test ผ่าน, guard แสดง error สวยงาม
- commit: dad90fb

---

## [2026-06-28 19:02] Add smt build subcommand

- ทำ: เพิ่ม CLI subcommand `smt build` ใน `cli.py` + 6 tests ใน `test_cli.py`
  - `_radius_from_element(el)`: helper แปลง k_in/k_out → signed design radius (0=tangent)
  - `_run_build(args)`: อ่าน PI CSV → `build_alignment_from_pi` → เขียน `elements_output.csv` + `controls_so_output.csv` + แสดงทั้งสองตารางใน terminal
  - parser registration: `smt build <alignment> [--out-dir DIR]`
  - import เพิ่ม `fpmath` สำหรับแปลง azimuth radian → degree
- คำสั่ง: `pytest -q`, `smt build test_data/SettingOutTest.csv --out-dir test_data/build_out/`
- ผล: PASS (393/393) — smoke test ผ่าน: elements_output.csv 32 rows, controls_so_output.csv 33 rows
- commit: 1a1efd1

---

## [2026-06-28] Refactor parse_pi_table — header-name lookup

- ทำ: แก้ `parse_pi_table` ใน `builders/alignment_builder.py` จาก position-based (r[0]..r[9]) → header-name lookup (case-insensitive)
  - เพิ่ม `_COL_ALIASES` dict: map header cell text → canonical key (รองรับ N/NORTHING, R/RADIUS, STA/CHAINAGE, TRANS/TRANSITION, LS/SPIRAL)
  - เพิ่ม `_parse_header(header_row)` → สร้าง `{key: col_index}` จาก header row
  - เพิ่ม `_get_cell(row, col_map, key)` → ดึงค่า safe, คืน '' ถ้า column ไม่มีหรือ row สั้นเกิน
  - `parse_pi_table` อ่าน `col_map` จาก rows[0] แล้วใช้ `_g(row, key)` แทน `r[index]` ตลอด
  - Columns ที่ไม่มีใน header → default (STA = 0.0; อื่นๆ = blank)
- ไม่แก้ test (existing `_HDR` headers ทุกตัว match alias แบบ case-insensitive อยู่แล้ว)
- คำสั่ง: `pytest -q`
- ผล: PASS (387/387)
- commit: fcd840c

---

## [2026-06-28] Bulk Field Cross-Check Feature

- ทำ: วางแผน (plan_bulk_crosscheck.md) + implement 3 ส่วนหลัก + 46 tests ใหม่
  - `parse_pi_table(rows)` ใน `builders/alignment_builder.py`: แปลง PI CSV → vertex list
    รองรับ simple circle, symmetric/asymmetric spiral, compound, angle point, BLOSS/COSINE/SINE
  - `FieldCrossCheckResult` + `bulk_cross_check()` ใน `check.py`: inverse (N,E → sta,offset)
    สำหรับ field survey points; ส่ง disc ผ่านไม่แตะ
  - `smt cross-check <alignment_pi.csv> <field.csv>` CLI subcommand ใน `cli.py`
  - Tests: TestParsePiTable (11 cases), TestBulkCrossCheck (8 cases), CLI tests (4 cases)
- คำสั่ง: pytest -q, ruff check src/, mypy src/smt/
- ผล: PASS (387/387) — mypy clean, ruff ไม่มี error ใหม่ (4 pre-existing E701 ไม่เกี่ยว)
- commit: 3aa8e30

## [2026-06-28] Add AlignmentBuilderV2.gs — EXT-001 no-curve PI (JS reference)

- ทำ: copy AlignmentBuilder.gs เป็น AlignmentBuilderV2.gs แล้วเพิ่ม 3 จุดสำหรับ EXT-001
  - `curveSubs_`: เพิ่ม early return `{subs:[], issue:null}` เมื่อ R หายหรือ R=0
  - `names_`: เพิ่ม guard `if (!subs || subs.length === 0)` → return IP scheme
  - `buildFromPI`: เพิ่ม angle-point branch → emit tangent + `'IP'` control point
  - เพิ่ม header comment "EXT-001: no-curve PI support — mirrors Python alignment_builder.py (commit cdf896d)"
- ต้นฉบับ `reference/AlignmentBuilder.gs` ไม่ถูกแตะ
- คำสั่ง: Write tool → `.git\smt_commit_msg.txt` แล้ว `git add` + `git commit -F`
- ผล: PASS — commit สำเร็จ ไม่กระทบ test ใดๆ
- commit: 7846cb6

---

## [2026-06-28] Part 2 — Defensive edge-case tests (vertical, crossfall, surface, check, builders)

- ทำ: เพิ่ม 23 tests ครอบ coverage gaps ที่ audit ระบุใน 6 ไฟล์ test
- ไฟล์ที่แก้:
  - `tests/test_vertical.py` (+6): grade continuity ที่ asymmetric arm boundary, empty segs→None, parse header-only/NaN/empty-lvc/short-row
  - `tests/test_crossfall.py` (+2): parse NaN sta_start ถูก skip, short row→default type V
  - `tests/test_surface.py` (+1): sta นอก alignment → ValueError propagated
  - `tests/test_check.py` (+4): empty controls→[], empty vchecks→[], far-outside sta→ValueError (horizontal + vertical)
  - `tests/builders/test_alignment_builder.py` (+5): spiral overflow/compound overflow→issues, Ls=0=simple circle, check_against_drawing empty control/unknown name skipped
  - `tests/builders/test_vertical_builder.py` (+5): L=0 VPI zero-lvc row, multiple overlaps→multiple issues, build_table([]), check_against_drawing empty drawing/unknown name skipped
- คำสั่ง: `pytest tests/ -q`
- ผล: PASS — 364/364 (เดิม 341 + 23 ใหม่), ไม่มี regression, ไม่แก้ engine
- commit: 0b75c5d

---

## [2026-06-28] Implement: No-Curve PI (Angle Point) support

- ทำ: เพิ่ม extension รองรับ PI ที่ไม่มีรัศมีโค้ง (angle point) ใน alignment_builder.py และ test ใหม่ 12 cases
- ไฟล์ที่แก้:
  - `src/smt/builders/alignment_builder.py`: แก้ 3 ฟังก์ชัน
    - `_build_curve_sub_elements`: เพิ่ม early return `([], None)` เมื่อ `not vert.get('R')` (ครอบคลุม missing R, R=0, R=None)
    - `_get_control_names`: เพิ่ม guard `if not subs: return {'start':'IP',...}`
    - `build_alignment_from_pi`: เพิ่ม branch `if not subs:` → emit tangent + ControlPoint('IP') + continue
  - `tests/builders/test_alignment_builder.py`: เพิ่ม class `TestNoCurvePI` (12 tests)
  - `session_logs/investigate_nocurve_pi.md`: รายงานสืบสวนก่อนลงมือ (อ่านอย่างเดียว)
- คำสั่ง: `pytest tests/builders/test_alignment_builder.py -v`, `pytest -q`
- ผล: PASS — 341/341 (เดิม 329 + 12 ใหม่), ไม่มี regression
- commit: cdf896d

---

## [2026-06-28] สร้าง docs/extensions.md (EXT-001)

- ทำ: สร้างไฟล์ `docs/extensions.md` — บันทึก extension แรกของโปรเจกต์ (no-curve PI / angle point)
- เนื้อหา: oracle limitation, สิ่งที่เพิ่ม, ที่มาคณิตศาสตร์ (AASHTO), commit ref, ตาราง 12 test cases
- คำสั่ง: `git add docs/extensions.md`, `git commit`, `git commit --amend` (ผู้ใช้แก้ message), `git push`
- ผล: PASS — commit 673da5d pushed to GitHub
- commit: 673da5d

---

## [2026-06-28] สืบสวน: No-Curve PI / Angle Point

- ทำ: อ่านและวิเคราะห์ว่าโปรเจกต์จัดการ PI ที่ไม่มีรัศมีโค้งอย่างไร (อ่านอย่างเดียว ไม่แก้โค้ด)
- ไฟล์ที่อ่าน: `reference/AlignmentBuilder.gs`, `src/smt/builders/alignment_builder.py`, `tests/builders/test_alignment_builder.py`
- ผล: เขียนรายงานลง `session_logs/investigate_nocurve_pi.md`
- สรุปผลการสืบสวน:
  - Oracle (.gs): ไม่รองรับ — ถ้าไม่มี `R` จะเกิด NaN propagation เงียบๆ
  - Python (.py): ไม่รองรับ — crash `KeyError: 'R'` ที่ `alignment_builder.py:86`
  - ฟังก์ชันที่ต้องแก้ (ถ้าจะ implement): `_build_curve_sub_elements` (early return เมื่อไม่มี R/compound), `_get_control_names` (guard empty subs), `build_alignment_from_pi` (branch ใหม่สำหรับ angle point)
  - จุดเสี่ยงหลัก: `det=sin(0)` division by zero เมื่อ collinear PI, `_get_control_names([])` IndexError, naming ซ้ำถ้ามีหลาย IP
- คำสั่ง: Read files only
- commit: ไม่มี (งานอ่าน/วิเคราะห์)

## [2026-06-24] Part 1 — Defensive edge-case tests (fpmath + wcb + alignment)

- ทำ: อ่าน review_logs/04_coverage_docstring.txt → วางแผน → เพิ่ม ~75 tests ครอบ Coverage ⚠️ ที่เหลือใน 3 ไฟล์
- ไฟล์ที่แก้:
  - `tests/test_fpmath.py` (+~35 tests): inf/nan guards, is_almost_equal branches, floor_mod (n=0 ZeroDivisionError, n<0, fractional), normalize_angle (0 / 2π boundary), angle_diff (same / π / 2π), kahan_sum (empty/single/negative/mixed), deg_to_rad/rad_to_deg (zero/negative/>360), packed DMS (zero/negative/carry), dms_to_rad (negative/zero/minutes-only)
  - `tests/test_wcb.py` (+~11 tests): azimuth cardinal directions + same-point, distance_2d (same-point/large), forward (zero/negative/north), inverse identical, offset (zero/negative/along=0)
  - `tests/test_alignment.py` (+~15 tests): radius_from_curvature (negative/unit/near-zero), make_element trans variants (BLOSS/None→CLOTHOID), parse_alignment_table (header-only/empty-radius), point_on_element (d=0/d=L), get_element_index (empty/before-start/junction), s2c outside→ValueError, first-station ok, c2s far-point→ValueError
- คำสั่ง: `pytest -q` / `ruff check` / `git commit`
- ผล: PASS (329/329) — ruff clean บนไฟล์ที่แก้ — mypy 0 errors
- commit: c40b3f3

## หมายเหตุ
- Part 2 (vertical, crossfall, surface, check, builders) รอ session ถัดไป
- Test carry case ต้องใช้ `dms_to_rad(0,59,59.997)` แทน deg_to_rad(59.5/3600) เพราะ float precision ทำให้ 59.5 → 59.4999... (ไม่ carry ด้วย sec_decimals=0)
- test_c2s_far_point_raises ต้องใช้ single-element alignment แทน golden alignment เพราะ spiral elements สามารถ absorb projection ของจุดไกลๆ ได้
