# Session Log

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
