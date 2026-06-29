# Session Log

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
