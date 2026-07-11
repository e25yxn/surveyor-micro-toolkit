# สืบสวน Phase 3 — ขอบเขตการ regenerate golden fixture — 2026-07-11

สืบสวนก่อนวางแผน Phase 3 (regenerate tests/golden/tables.json + reference/tables.json ให้ตรงกับ
Phase 1 ที่แก้ core engine COSINE arc-length inversion ไปแล้ว — session_logs/plan_cosine_arclength_core_fix.md)
**ยังไม่แก้ไฟล์ใดๆ ในรอบนี้ เป็นรายงานสืบสวนล้วน**

---

## 1. ยืนยันสถานะปัจจุบัน

`git status`:
- Modified: `src/smt/alignment.py`, `tests/test_alignment.py`
- Untracked: `session_logs/plan_cosine_arclength_core_fix.md`, `test_data/SMT_TEST_CLOTHIOD.csv`,
  `test_data/SettingOutTest555.xml`

`git diff --stat -- src/smt/alignment.py tests/test_alignment.py`:
```
 src/smt/alignment.py    | 155 +++++++++++++++++++++++++++++++++++++-----------
 tests/test_alignment.py | 106 ++++++++++++++++++++++++++-------
 2 files changed, 206 insertions(+), 55 deletions(-)
```
ตรงกับตัวเลขที่คาดไว้ (206 insertions, 55 deletions) เป๊ะ — ยืนยันว่า Phase 1
(`session_logs/plan_cosine_arclength_core_fix.md`) ถูก apply ไว้ในต้นไม้แล้วจริง ยังไม่ commit.

## 2. กระบวนการ regenerate golden fixture ที่เคยใช้มาก่อน (2 รอบ)

**ที่มาของ fixture**: `tests/golden/tables.json` และ `reference/tables.json` เดิมมาจาก JS oracle
(AllTests 45/45) แต่หลังจากมี extension ที่เบี่ยงจาก oracle (เช่น COSINE closed-form) ทั้งสองไฟล์
regenerate ใหม่จาก `build_alignment_from_pi` ของ Python เอง ไม่ใช่จาก oracle อีกต่อไป

**กลไก reconstruction**: `tests/builders/test_alignment_builder.py::_make_vertices` (บรรทัด 65-104)
สร้าง PI vertex list ย้อนกลับจาก golden elements/controls เดิม (tangent-line intersection ที่แต่ละ
กลุ่มโค้ง, พารามิเตอร์ R/Ls/trans/compound hard-coded ไว้ในโค้ดนี้เอง 9 กลุ่ม) แล้ว fixture
`result` = `ab.build_alignment_from_pi(vertices)` — นี่คือกลไกเดียวกับที่ทั้ง 2 รอบก่อนหน้าใช้
regenerate

**ขั้นตอนที่เคยใช้ (จาก session_logs/latest.md, entry "[2026-07-05] สรุปรวม...")**:
1. เขียนสคริปต์ regenerate แยกใน scratchpad (ชื่อ `regenerate_cosine_golden_fixture.py` ทั้ง 2 รอบ
   — ไม่เคย commit ตัวสคริปต์เอง, ไม่พบไฟล์นี้หลงเหลือในโปรเจกต์ปัจจุบัน — `Glob` ยืนยันว่าไม่มี
   `**/regenerate*golden*.py` เหลืออยู่)
2. **dry-run** แสดง diff เต็มให้ผู้ใช้ตรวจก่อน (ไม่เขียนไฟล์จริง)
3. เมื่อได้รับอนุมัติ **apply จริง** ทับ `tests/golden/tables.json` และ `reference/tables.json`
4. **byte-compare** สองไฟล์หลัง apply ว่าเหมือนกันทุกตัวอักษร (ทั้งสองไฟล์ต้องตรงกันเป๊ะ เพราะเก็บ
   ข้อมูลชุดเดียวกัน)
5. รัน `pytest -q` ยืนยันจำนวน pass/xfail ตามที่คาด แล้วจึง commit

รอบแรก (commit `aa8038c`, ส่วนหนึ่งของ COSINE closed-form fix): 20 element rows + 20 control rows
เปลี่ยน — mismatch จากการสลับ Simpson→closed-form (a=L/X approximation) ของ COSINE เอง
รอบสอง (commit เดียวกันช่วง, หลังแก้ `_build_curve_sub_elements`): อีก 20 element rows + 20
control rows เปลี่ยน — mismatch จากการเปลี่ยน `theta_in`/`theta_out` จากสูตรเชิงเส้น `Ls/(2R)` เป็น
มุมหมุนจริงผ่าน `calculate_exit_state`

## 3. ตรวจ alignment_builder.py — ต้องแก้เพิ่มหรือแค่ regenerate fixture พอ

อ่าน `src/smt/builders/alignment_builder.py` บรรทัด 85-173 (ครอบ `_build_curve_sub_elements`,
`_spiral_turning_angle`, `_calculate_end_displacement`) ยืนยันตรงกับที่
`session_logs/investigate_cosine_totaly_theta_export.md` ระบุไว้:

- `_build_curve_sub_elements` (บรรทัด 95-102) เรียก `_spiral_turning_angle(R, ls_in, trans_in)` /
  `_spiral_turning_angle(R, ls_out, trans_out)` แล้ว — **ไม่มีสูตรเชิงเส้น `Ls/(2R)` หลงเหลืออยู่
  แล้ว** (ถูกแก้ไปตั้งแต่ 2026-07-05 รอบสอง ตาม comment บรรทัด 99-100: "EXTENSION: beyond oracle —
  reference/AlignmentBuilder.gs (lines 53-54) still assumes theta=Ls/(2R); real turning angle
  needed for the COSINE closed form")
- `_spiral_turning_angle` (บรรทัด 139-150) สร้าง synthetic SPIN element แล้วเรียก
  `calculate_exit_state(el).azimuth - el.azimuth` ตรงๆ — เรียกเข้า `alignment.py` โดยตรง ไม่มี
  hardcode สูตรใดๆ ของตัวเอง ดังนั้น Phase 1 ที่แก้ `calculate_point_on_element`/
  `calculate_exit_state` ใน `alignment.py` จะไหลเข้ามาที่ฟังก์ชันนี้อัตโนมัติโดยไม่ต้องแก้โค้ดตรงนี้เลย
- `_calculate_end_displacement` (บรรทัด 153-173) เรียก `calculate_exit_state(el)` ต่อ sub-element
  เช่นกัน (บรรทัด 170) — ก็ได้รับผลของ Phase 1 อัตโนมัติเหมือนกัน
- grep ทั้งไฟล์ไม่พบจุดอื่นที่ hardcode สูตร COSINE หรือค่าคงที่ที่ต้อง sync กับ core engine เพิ่ม

**สรุปข้อ 3**: ยืนยันแล้วว่า **ไม่ต้องแก้โค้ด builder เพิ่ม** — builder ทั้งหมด delegate ไปที่
`calculate_exit_state`/`calculate_point_on_element` ใน `alignment.py` อยู่แล้ว Phase 1 แก้ที่ core
engine จุดเดียวก็ไหลเข้ามาถึง builder เองผ่านฟังก์ชันที่มีอยู่แล้วทั้งหมด — Phase 3 คือ
regenerate fixture ล้วนๆ ไม่มีจุดโค้ดอื่นที่ต้อง sync เพิ่ม

## 4. รายละเอียด pytest 9 ตัวที่ fail (รันจริง ไม่ใช่แค่สรุป)

รัน `pytest -q` เต็ม (พร้อม Phase 1 อยู่ในต้นไม้): **9 failed, 481 passed** (ไม่มี xfail มาสก์ใดๆ
อยู่แล้ว — grep `xfail` เจอแค่ comment อ้างอิงในบรรทัด 344-347 ของ test_alignment_builder.py ไม่ใช่
mark จริง)

รายชื่อทั้ง 9 ตัว พร้อมตัวเลข error จริงจากการรันแยก (`-v` ครบทุกตัว):

| # | test | error ที่วัดได้ |
|---|---|---|
| 1 | `test_alignment_builder.py::TestGoldenElementGeometry::test_element_ne_within_tolerance` | element[12] N: built=18896.335553 golden=18896.318300 (diff 17.3mm) |
| 2 | `test_alignment_builder.py::TestGoldenElementGeometry::test_element_stations_within_tolerance` | element[12] sta_end: built=2484.827686 golden=2484.765600 (diff 62.1mm) |
| 3 | `test_alignment_builder.py::TestGoldenControlPoints::test_control_ne_within_1mm` | control[12] (SC) N diff 17.3mm |
| 4 | `test_alignment_builder.py::TestCheckAgainstDrawing::test_all_controls_pass_1mm_tolerance` | SC gap=30.88mm, CS gap=30.95mm |
| 5 | `test_alignment.py::test_chain_has_no_gaps` | gap 12->13 = 31.110mm (12.768 arcsec), gap 14->15 = 31.269mm (12.768 arcsec) |
| 6 | `test_alignment.py::test_control_points` | SC@2249.25 err=(17.4mm, 25.8mm) |
| 7 | `test_alignment.py::test_control_point_parametrized[SC@2249.25]` | N got 18896.3357 expected 18896.3183 (17.4mm) |
| 8 | `test_alignment.py::test_exit_state_matches_next_entry` | element 11->12 gap 31.110mm |
| 9 | `test_check.py::test_check_horizontal_all_pass` | SC@2249.25 gap=0.031110m (31.1mm) > 2mm tolerance |

**ยืนยัน single root cause จริง**: ทุกตัวชี้ไปที่จุดเดียวกัน — รอยต่อ SPIN-COSINE เข้า circular arc
ที่ station ≈2249.25 (control point SC ของกลุ่มโค้งที่ 4, R=500 L=70) ขนาด gap 31.11mm ตรงกับตัวเลข
ที่ `session_logs/plan_cosine_arclength_core_fix.md` ทำนายไว้ล่วงหน้า (`L - X` ที่ R=500/L=70 =
31.102mm, ต่างจากที่วัดจริง 31.110mm แค่ 0.008mm) — เป็นผลของ `_sine_halfwave_point` ที่ตอนนี้คืนค่า
`x = a*X` จริง (ไม่ใช่ `x = d` ตรงๆ แบบเดิม) ทำให้ตำแหน่งจุดปลาย SPIN-COSINE ขยับ

พบ **gap ที่สอง** ที่ `test_chain_has_no_gaps` ไม่ได้ถูกพูดถึงในแผน Phase 1 ตรงๆ: รอยต่อ 14->15
(31.269mm) — นี่คือฝั่ง SPOUT-COSINE ออกจาก circular arc กลับสู่ tangent (จุด CS) ของกลุ่มโค้ง
เดียวกัน ขนาดใกล้เคียงกับ gap แรกมาก (31.269 vs 31.110mm, ทั้งคู่ระดับ `L-X` ≈31.1mm) — สอดคล้องกับ
กลไกเดียวกันที่เกิดที่ปลายทั้งสองข้างของ transition COSINE เดียวกัน ไม่ใช่สาเหตุอื่น (ยืนยันด้วยข้อ 5
ด้านล่าง — ทั้งสอง gap มาจาก PI group เดียวกัน กลุ่มที่ 4)

**สรุปข้อ 4**: ทั้ง 9 test fail มีสาเหตุเดียวกันจริง (ไม่มีสาเหตุอื่นปน) คือ COSINE curve group
เดียว (R=500, L=70, elements index 11-14, controls TS/SC/CS/ST ของกลุ่มที่ 4) ที่ตำแหน่ง/theta ที่
รอยต่อทั้งสองข้าง (SC และ CS) เปลี่ยนไปตาม Phase 1

## 5. ขอบเขต Phase 3 เทียบกับ 2 รอบก่อนหน้า

รัน `_make_vertices` + `build_alignment_from_pi` จริงในเครื่อง (import ตรงจาก
`tests/builders/test_alignment_builder.py`) เทียบกับ `tests/golden/tables.json` ปัจจุบัน:

- **grep ยืนยัน**: golden fixture มี COSINE แค่ **1 กลุ่มเดียวเท่านั้น** ในทั้งหมด 9 กลุ่มโค้ง —
  element index 11 (SPIN) และ 13 (SPOUT) ทั้งคู่ R=500 (ตรงกับ groups list ใน `_make_vertices`
  บรรทัด 80: `(11, 14, 10, 14, {'R': 500, 'Ls': 70, 'trans': 'COSINE'})`)
- diff เต็ม (ทุก element/control เทียบ golden, threshold 1e-6 ธรรมดา) แสดงว่า element **ทุกตัว**
  (30/30) และ control **เกือบทุกตัว** (29/31) ต่างจาก golden เกิน 1e-6 — แต่ขนาดต่างกันคนละระดับ
  ชัดเจน 2 กลุ่ม:
  1. **Noise ระดับ reconstruction เดิม** (~0.00001–0.0002m, มีอยู่แล้วในทุกกลุ่มโค้งทั้ง 9 กลุ่ม
     ไม่ใช่ผลจาก Phase 1) — เกิดจาก `_make_vertices`'s docstring ระบุไว้เองว่า PI ที่ reconstruct
     กลับมามีความละเอียดแค่ ~1e-4 m (จำกัดโดยการปัดเศษ 4 ตำแหน่งทศนิยมในไฟล์ fixture) — เป็นเหตุผล
     ที่ test เดิมตั้ง tolerance ไว้ที่ 1e-3/2e-3m ไม่ใช่ exact match อยู่แล้ว ไม่ใช่ของใหม่จาก Phase 1
  2. **การเปลี่ยนแปลงจริงจาก Phase 1** (17–27mm) — เกิดเฉพาะที่ element 11-14 / control 11-14
     (กลุ่มที่ 4, COSINE) เท่านั้น — สูงกว่า noise พื้นฐานถึง ~100-200 เท่า ตรงกับที่ pytest จับได้
  3. **Station offset สะสม** (~0.0623m คงที่) ปรากฏใน `sta_start`/`sta_end` ของ**ทุก element ตั้งแต่
     index 12 เป็นต้นไปจนจบ** (18 element, ไม่ใช่แค่กลุ่ม COSINE) — เพราะ station เป็นผลรวมความยาว
     สะสมจาก BP; ความยาว circular arc ของกลุ่ม COSINE (`R * delta_circular`) เปลี่ยนไปเล็กน้อยตาม
     theta_in/theta_out ใหม่จาก Phase 1 (ผ่าน `_spiral_turning_angle`) ทำให้ station ของทุก element
     หลังจากนั้นขยับตามคงที่ — **แต่ N,E ของ elements 15+ ไม่ขยับตาม** (อยู่ในช่วง noise พื้นฐานเดิม
     เท่านั้น) เพราะแต่ละกลุ่มโค้งถัดไปถูก reconstruct positioned อิสระจาก golden TS/ST เดิม
     (fixed coordinates) ไม่ได้ chain ต่อจาก position สะสม

**เทียบกับ 2 รอบก่อนหน้า (20 element rows + 20 control rows เปลี่ยนทั้งคู่)**:
- Phase 3 นี้**แคบกว่ามาก**ในแง่ตำแหน่ง N,E ที่เปลี่ยนจริง (มีนัยสำคัญ) — กระทบแค่ **1 PI group จาก 9
  กลุ่ม** (กลุ่มที่ 4 เท่านั้น, element 11-14 / control 11-14 รวม 4+4 = 8 rows) เทียบกับ 2 รอบก่อนที่
  กระทบ 20 rows (เกือบทุกกลุ่มที่มี spiral เพราะตอนนั้นแก้ `_build_curve_sub_elements` ซึ่งเป็นฟังก์ชัน
  กลางที่ใช้ร่วมกันทุก transition — แม้จะพิสูจน์แล้วว่า CLOTHOID/BLOSS/SINE ไม่เปลี่ยนค่าจริง (1e-16
  noise) แต่ตอนนั้นยังไม่มีเครื่องมือแยก "noise พื้นฐาน" ออกจาก "การเปลี่ยนแปลงจริง" ชัดเจนแบบนี้
  จึงนับรวมเป็น 20 rows เปลี่ยนหมด)
- Phase 3 นี้**กว้างกว่า**ในแง่ **คอลัมน์ station** — กระทบทุก element ตั้งแต่ index 12 เป็นต้นไป
  (18 จาก 30 element rows) แม้ว่า N,E ของ element เหล่านั้นจะไม่เปลี่ยนจริง (การ regenerate ต้องเขียน
  station ใหม่ทั้ง 18 แถวนี้ด้วย ไม่ใช่แค่ 4 แถวของกลุ่ม COSINE)
- สรุป: Phase 3 กระทบ **1 ใน 9 PI groups** (เท่ากับรอบแรกที่กระทบเฉพาะ COSINE เหมือนกัน แต่รอบแรก
  ยังไม่มี `_spiral_turning_angle` fix จึงกระทบแค่ N,E/theta ของกลุ่ม COSINE เดียวไม่ลาม station คอลัมน์
  ไปกลุ่มอื่น) ขอบเขตจึงอยู่ระหว่างรอบแรกกับรอบสอง — แคบกว่าทั้งสองรอบในแง่ตำแหน่งที่มีนัยสำคัญจริง
  แต่กว้างกว่ารอบแรกในแง่จำนวนแถว station ที่ต้องเขียนทับ (เพราะกระทบทุกอย่างที่อยู่หลังกลุ่ม COSINE)

## สรุปรวม

1. สถานะ git ตรงกับที่คาด (206/-55) — Phase 1 อยู่ในต้นไม้แล้ว ยังไม่ commit
2. กระบวนการ regenerate ที่เคยใช้ 2 รอบ: เขียนสคริปต์ scratchpad (ไม่ commit) → dry-run diff ให้ตรวจ
   → apply → byte-compare สองไฟล์ → pytest ยืนยัน → commit
3. **ไม่ต้องแก้ `alignment_builder.py` เพิ่มเลย** — `_spiral_turning_angle`/
   `_calculate_end_displacement` เรียก `calculate_exit_state` ตรงๆ อยู่แล้ว รับผล Phase 1
   อัตโนมัติ ไม่มี hardcode ใดๆ ที่ต้อง sync
4. 9 test ที่ fail มีสาเหตุเดียวกันจริง 100% — COSINE curve group เดียว (R=500/L=70, กลุ่มที่ 4)
   ทั้งสองรอยต่อ (SC เข้า, CS ออก) ขยับ ~31mm ตรงกับ `L-X` ที่ทำนายไว้ในแผน Phase 1
5. ขอบเขต Phase 3 แคบกว่า 2 รอบก่อนในแง่ N,E ที่เปลี่ยนจริง (1 กลุ่มจาก 9, 8 rows) แต่กว้างกว่าในแง่
   คอลัมน์ station (18 จาก 30 element rows ต้องเขียนทับเพราะ station สะสมต่อกัน)

## อ้างอิง
- `session_logs/plan_cosine_arclength_core_fix.md` — แผน Phase 1 ที่ทำนาย 31.110mm gap ไว้ล่วงหน้า
- `session_logs/investigate_cosine_arclength_inversion.md` — validate Simpson s(a)+bisection
- `session_logs/investigate_cosine_totaly_theta_export.md` — จุดที่ยืนยันว่าต้องแก้ core engine
- `session_logs/investigate_build_curve_sub_elements_fix.md`,
  `session_logs/investigate_cosine_builder_mismatch_20260705.md` — ประวัติการแก้ builder รอบก่อน
- `session_logs/report_xfail_mismatch_20260705.md` — วิธีตรวจผล xfail จริงเทียบที่คาดไว้ (ใช้อ้างอิง
  ระเบียบวิธีเดียวกันสำหรับ Phase 3)
