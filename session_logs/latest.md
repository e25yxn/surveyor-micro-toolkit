# Session Log

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
