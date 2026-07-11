# สืบสวน Phase 2 — LandXML COSINE totalY/tanShort export — 2026-07-11

ต่อยอดจาก `session_logs/investigate_cosine_totaly_theta_export.md` (2026-07-07) ที่สรุปว่า
theta/totalY/tanShort ของ COSINE ยัง**ใช้ค่าประมาณเดิม** และต้องแก้ core engine ไม่ใช่แค่
`landxml.py` — ตอนนี้ core engine (`alignment.py`) แก้ไปแล้วจริงใน Phase 1 + regenerate fixture
ใน Phase 3 (commit `d8ebedd`) สืบสวนว่า totalY/tanShort ใน LandXML export ได้รับผลจาก Phase 1
อัตโนมัติแล้วหรือยังต้องแก้เพิ่ม **ยังไม่แก้โค้ดใดๆ ในรอบนี้ เป็นรายงานสืบสวนล้วน**

---

## 1. `_spiral_geometry` เต็มฟังก์ชัน (src/smt/landxml.py บรรทัด 88-115)

```python
def _spiral_geometry(R: float, length: float, transition: str, theta_rad: float) -> tuple[float, float, float, float]:
    """(totalX, totalY, tanLong, tanShort) for a spiral, computed canonically:
    a synthetic Element at the origin (n=0, e=0, azimuth=0) curving from
    k_in=0 to k_out=1/R over [0, length], independent of the spiral's real
    position, direction, or SPIN/SPOUT role in the alignment.

    COSINE transition: totalX is overridden with the closed-form tangent-
    projected length (calculate_sine_halfwave_tangent_length) instead of the
    raw value calculate_point_on_element returns at d=length, which equals
    `length` itself (known limitation; see
    session_logs/investigate_totalx_landxml_fix.md). tanLong changes as a
    direct consequence (tanLong = totalX - totalY/tan(theta)); totalY/
    tanShort still use the d=length approximation -- a separate, smaller,
    already-documented known limitation (see alignment.py module docstring
    "Known limitations").
    """
    synthetic = Element(
        type='SPIN', sta_start=0.0, sta_end=length,
        n=0.0, e=0.0, azimuth=0.0,
        k_in=0.0, k_out=1.0 / R, transition=transition,
    )
    state = calculate_point_on_element(synthetic, length)
    total_x, total_y = state.n, state.e
    if transition == 'COSINE':
        total_x = calculate_sine_halfwave_tangent_length(length, R)
    tan_long = total_x - total_y / math.tan(theta_rad)
    tan_short = total_y / math.sin(theta_rad)
    return total_x, total_y, tan_long, tan_short
```

**สิ่งสำคัญที่พบทันที**: docstring ของฟังก์ชันนี้ (และของ `alignment.py`'s module docstring
"Known limitations" ที่มันอ้างอิงถึง) เขียนไว้ว่า totalY/tanShort **"still use the d=length
approximation"** — ข้อความนี้เขียนขึ้นตอน Phase 1 (ก่อน apply จริง) เป็นการ**คาดการณ์ล่วงหน้า** ไม่ใช่
ผลที่ยืนยันจริงหลัง Phase 1 apply แล้ว — สืบสวนรอบนี้พบว่าคาดการณ์นั้น**ผิด** (ดูข้อ 2-3)

## 2. total_y มาจากไหน — เรียกผ่าน calculate_point_on_element จริง (ฟังก์ชันเดียวกับที่ Phase 1 แก้)

`total_y = state.e` โดย `state = calculate_point_on_element(synthetic, length)` — เรียก
`calculate_point_on_element` ตรงๆ ไม่มีสูตรแยกของตัวเองใน `landxml.py` เลย และ **ไม่มี override
สำหรับ total_y** (มีแค่ override ของ total_x เท่านั้น ที่บรรทัด 111-112) — ต่างจากที่ docstring บอกไว้
ว่า "totalY still use the d=length approximation" (ราวกับมันมีสูตรของตัวเองที่ค้างอยู่)

เพราะ `synthetic.sta_end - synthetic.sta_start == length` พอดี การเรียก
`calculate_point_on_element(synthetic, length)` คือการประเมินที่ `d == length` เป๊ะ — ตรงกับเงื่อนไข
`abs(d - length) < 1e-9` ที่ Phase 1 เพิ่ม short-circuit `a=1.0` (exact closed form) เข้าไปใน
`_sine_halfwave_point` พอดี ดังนั้น total_y ที่ได้ควรเป็นค่า a=1 exact อัตโนมัติ

**ยืนยันด้วยการรันจริง** เทียบกับ Civil 3D ground truth 2 จุดจาก
`session_logs/investigate_sinehalfwave_formula.md` (บรรทัด 21, 25) และจุดที่ 3 จาก
`session_logs/plan_cosine_arclength_core_fix.md` (Group 1 test):

| R,L | totalY จาก `_spiral_geometry` (รันจริงตอนนี้) | totalY ground truth | diff |
|---|---|---|---|
| R=900,L=100 | 1.6510623161163522 | 1.651062316115 (Civil 3D จริง) | 1.35e-13 |
| R=250,L=50 | 1.4840930725353927 | 1.484093072531 (Civil 3D จริง) | 4.39e-12 |
| R=500,L=70 | 1.4557579182062428 | 1.4557579182062208 (a=1 closed form) | 2.20e-14 |

ทั้งสามจุด diff อยู่ระดับ floating-point noise (1e-12 ถึง 1e-14) — **totalY ถูกต้องอัตโนมัติแล้ว**
ไม่ต้องแก้โค้ดเพิ่ม

**พบเพิ่ม (นอกเหนือคำถามเดิม)**: totalX override (บรรทัด 111-112) ก็**กลายเป็น redundant แล้วด้วย**
— ตรวจสอบว่า `state.n` (ค่าดิบจาก `calculate_point_on_element` ที่ d=length โดยไม่ผ่าน override)
ตอนนี้เท่ากับ `calculate_sine_halfwave_tangent_length(length, R)` **เป๊ะทุกบิต** (diff=0.000e+00
ทั้ง 3 จุด R/L) เพราะ `x = a*X` และ `a=1.0` พอดีที่ d=length หลัง Phase 1 — override นี้ไม่ผิด
(ยังให้ผลถูกต้องเหมือนเดิม) แต่ตอนนี้ไม่จำเป็นอีกต่อไป เป็นโค้ดที่ทำงานซ้ำกับสิ่งที่ core engine
ให้มาอยู่แล้ว ไม่ใช่บั๊ก แค่สังเกตไว้เผื่อ cleanup ในอนาคต

## 3. tanShort มาจากไหน — คำนวณจาก total_y/theta_rad ที่ถูกต้องแล้ว ไม่มีสูตรแยก

`tan_short = total_y / math.sin(theta_rad)` — ไม่มีสูตรแยกของตัวเอง เป็นแค่การหารตรงๆ จาก total_y
(ยืนยันถูกต้องแล้วในข้อ 2) และ `theta_rad` ซึ่งมาจาก `_theta_rad(el.azimuth, exit_az)` ที่เรียกจาก
`export_alignment_landxml` (บรรทัด 236, 259) — `exit_az` มาจาก `_exit_azimuth()` ซึ่งอ่านค่า azimuth
ของ element ถัดไปที่ถูก build จริงผ่าน `build_alignment_from_pi` (เรียก `calculate_exit_state` ที่
ถูกแก้ใน Phase 1 เช่นกัน — ยืนยันแล้วใน `session_logs/investigate_phase3_golden_regen_scope.md`
ว่า chain gap ปิดสนิทหลัง Phase 3) ดังนั้น theta_rad ก็ถูกต้องอัตโนมัติเช่นกัน ไม่ใช่แค่ totalY

**ยืนยันด้วย Civil 3D ground truth จริง** (`investigate_sinehalfwave_formula.md` บรรทัด 43, จาก
SMT_TEST_ALINGMENT2.xml จริง R=250 L=50): tanShort จริงจาก Civil 3D = 14.928353346451 เทียบกับที่
คำนวณได้ตอนนี้ = 14.928353346471804 — diff = 2.08e-11 (floating-point noise) **tanShort ถูกต้อง
อัตโนมัติแล้วเช่นกัน**

## 4. Smoke test จริง — `smt export-landxml test_data/SettingOutTest.csv`

รันจริง (`python -m smt.cli export-landxml test_data/SettingOutTest.csv --name
SettingOutTest_Phase2Check --out ...`) แล้วตรวจ `<Spiral spiType="sineHalfWave">` (กลุ่ม COSINE
เดียวในไฟล์นี้ R=500 L=70 — กลุ่มเดียวกับที่ Phase 3 แก้):

```xml
<Spiral rot="cw" radiusStart="INF" radiusEnd="500.000000" spiType="sineHalfWave"
        length="70.000000" theta="4.002400" totalX="69.968898" totalY="1.455758"
        tanLong="49.163112" tanShort="20.856653">
<Spiral rot="cw" radiusStart="500.000000" radiusEnd="INF" spiType="sineHalfWave"
        length="70.000000" theta="4.002400" totalX="69.968898" totalY="1.455758"
        tanLong="49.163112" tanShort="20.856653">
```

SPIN และ SPOUT รายงานค่าเท่ากันทุกตัว (mirror symmetry ตามที่คาด) ตรงกับ a=1 exact closed-form
target ที่คำนวณไว้ล่วงหน้า (theta=4.002399624673551°, totalY=1.4557579182062208,
tanShort=20.856652643241134) ตรงกันถึงหลักทศนิยมที่แสดงในไฟล์ (6 ตำแหน่ง) ทุกค่า

## 5. สรุป — Phase 2 ตกกรณีไหน

**กรณี (ก) — ถูกแก้อัตโนมัติแล้วจริง ไม่ต้องแก้โค้ด `landxml.py` เพิ่มเลย**

เหตุผล: `_spiral_geometry` ไม่มีสูตรของตัวเองสำหรับ totalY/tanShort เลย ทั้งสองค่า delegate ไปที่
`calculate_point_on_element`/`calculate_exit_state` ใน `alignment.py` โดยตรง (เหมือนที่
`alignment_builder.py` ทำใน Phase 3) Phase 1 แก้ที่จุดเดียวก็ไหลเข้ามาถึง export layer เองแล้ว
ยืนยันด้วย ground truth จริง 2 จุด (Civil 3D) + จุดปิด-ฟอร์มที่ 3 + smoke test จริง 1 ไฟล์ ครบทุกทาง

**งานที่เหลือ (ไม่ใช่การแก้โค้ดคำนวณ):**
1. **เขียน test ใหม่ใน `tests/test_landxml.py`** — ตอนนี้ยังไม่มี test ใดยืนยันค่า totalY/tanShort
   ของ COSINE กับ ground truth จริงเลย (`test_spin_geometry_attributes` ใช้ CLOTHOID ไม่ใช่ COSINE;
   `test_cosine_total_x_uses_closed_form_not_arc_length` และ
   `test_cosine_spin_spout_total_x_match` เช็คแค่ totalX กับ SPIN==SPOUT symmetry ไม่เช็คค่า
   totalY/tanShort สัมบูรณ์เทียบ ground truth) — เป็นช่องว่างที่ควรปิดด้วย regression test
2. **แก้ docstring ที่ล้าสมัยแล้ว 2 จุด** (ข้อความยืนยันผิดหลัง Phase 1 apply จริง):
   - `landxml.py::_spiral_geometry` docstring (บรรทัด 98-102) — ยังเขียนว่า "totalY/tanShort still
     use the d=length approximation" ทั้งที่ตอนนี้ถูกต้องแล้ว
   - `alignment.py` module docstring, Known limitation (3) — ยังเขียนว่า "landxml.py's
     _spiral_geometry still computes totalY/tanShort from the same d=length evaluation... has not
     itself been updated... remain a smaller, still-open item... until a follow-up phase updates
     the export layer" — ข้อความนี้เขียนไว้ตอนวางแผน Phase 1 (ก่อน apply) เป็นการคาดการณ์ที่ผิด
     ไม่ใช่ข้อเท็จจริงหลัง apply จริง
3. **CLAUDE.md Known limits** — บรรทัดที่พูดถึง COSINE ("...ยังมี known limitation ย่อยที่ยังไม่แก้:
   x≈s เป็นค่าประมาณ...") ก็ล้าสมัยไปแล้วทั้งหมดตั้งแต่ Phase 1 (ไม่ใช่แค่ประเด็น totalY/tanShort ใน
   landxml.py) — พบระหว่างทางแม้จะไม่ใช่จุดโฟกัสของรายงานนี้โดยตรง
4. **totalX override ที่ตอนนี้ redundant** (ข้อ 2 ด้านบน) — ไม่ผิด แต่ซ้ำซ้อนกับสิ่งที่ core engine
   ให้มาเองแล้ว เป็นเป้าหมาย cleanup ที่เป็นไปได้ในอนาคต ไม่ใช่บั๊กที่ต้องรีบแก้

**ไม่มีจุดใดที่ต้องแก้ตัวเลข/สูตรคำนวณจริงในรอบนี้** — ต่างจาก Phase 1/Phase 3 ที่เป็นการแก้ core
engine + regenerate fixture, งานที่เหลือของ Phase 2 ทั้งหมดเป็นเอกสาร + test coverage เท่านั้น

## อ้างอิง
- `session_logs/investigate_cosine_totaly_theta_export.md` — จุดที่สรุปไว้ก่อนหน้าว่าต้องแก้ core
  engine (สรุปนั้นถูกต้อง แต่ยังไม่เคยตรวจว่า export layer ได้ผลพลอยได้จาก Phase 1 หรือไม่)
- `session_logs/plan_cosine_arclength_core_fix.md` — Phase 1 ที่แก้ core engine จริง (Group 1 test
  ground truth ที่ใช้ตรวจในรายงานนี้)
- `session_logs/investigate_phase3_golden_regen_scope.md` — Phase 3 fixture regen ที่ยืนยัน chain
  gap ปิดสนิทแล้ว (สนับสนุนว่า theta_rad ที่ export ก็ถูกต้องอัตโนมัติเช่นกัน)
- `session_logs/investigate_sinehalfwave_formula.md` — Civil 3D ground truth จริง 2 จุด (R=900/L=100,
  R=250/L=50) ที่ใช้ยืนยัน totalY/tanShort ในรายงานนี้
- `session_logs/investigate_totalx_landxml_fix.md` — ประวัติการแก้ totalX ครั้งก่อน (บริบทของ override
  ที่ตอนนี้พบว่า redundant)
