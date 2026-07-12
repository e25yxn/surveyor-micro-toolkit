# สืบสวนสโคป — ป้ายกำกับ default "CLOTHOID" บน element ประเภท T/C

วันที่ 2026-07-12
ประเภทงาน สืบสวน/รายงานเท่านั้น ยังไม่แก้ไฟล์ใดๆ ทั้งสิ้น

บริบท คอลัมน์ Transition ตั้งค่า default เป็น 'CLOTHOID' ทุกครั้งที่ไม่ได้ระบุ แม้กับ
element ประเภท Tangent (T) และ Circular (C) ที่พิสูจน์แล้วหลายรอบว่าไม่เคยอ่านคอลัมน์นี้
ในการคำนวณเลย (T/C branch ใน calculate_point_on_element/SMT_PointOnElement
return ก่อนแตะ transition เสมอ) ผู้ใช้ขอสืบสวนสโคปก่อนวางแผนแก้จริง

---

## 1. ทุกจุดที่ 'CLOTHOID' ถูกใช้เป็นกลไก default (เต็มทุกจุด พร้อมบรรทัด)

**Python `src/smt/alignment.py`:**
```
:303  def make_element(..., trans: str | None = 'CLOTHOID', ...)
:325  tr = str(trans).strip().upper() if trans else 'CLOTHOID'   # ใน make_element
:349  make_element(type_, sta_start, sta_end, n, e, az_deg, radius, None, trans or 'CLOTHOID')  # ใน parse_alignment_table
```

**VBA `reference/vba/SMT_Alignment.bas`:**
```
:463  If Len(Trim(transStr)) = 0 Then transStr = "CLOTHOID"   # ใน SMT_SolveForward
:517  If Len(Trim(transStr)) = 0 Then transStr = "CLOTHOID"   # ใน SMT_SolveInverse
```

**พบใหม่ ยังไม่เคยบันทึกไว้ที่ไหนมาก่อน — `src/smt/cli.py:135`:**
```python
transition_val = '' if el.type in ('T', 'C') else el.transition
```
อยู่ใน `_run_build` ตอนเขียน `elements_output.csv` นี่คือ **patch เฉพาะจุดที่มีอยู่แล้ว**
เพื่อลบค่า 'CLOTHOID' ออกจากการแสดงผล CSV สำหรับ T/C — การมี patch นี้อยู่แล้ว
**ยืนยันโดยตัวมันเอง** ว่า `Element.transition` ภายในสำหรับ T/C จริงๆ แล้วมีค่า
'CLOTHOID' อยู่ (ถ้าไม่มีค่านี้จริง patch นี้ก็ไม่จำเป็นต้องมี) และยืนยันว่าปัญหานี้เคยถูก
สังเกตเห็นและแก้ไปแล้วครั้งหนึ่ง ที่จุด export จุดเดียวเท่านั้น

**ที่มาของ pattern นี้คือ oracle เอง — `reference/Alignment.gs:84`:**
```javascript
var tr = trans ? String(trans).trim().toUpperCase() : 'CLOTHOID';
```
oracle .gs (ผ่าน AllTests 45/45 แล้ว) ตั้งค่า default เป็น 'CLOTHOID' แบบไม่มีเงื่อนไข
ให้ทุกชนิด element ตั้งแต่ต้น ทั้ง Python และ VBA พอร์ตพฤติกรรมนี้มาตรงๆ ตามกฎ
CLAUDE.md ("Python MUST match oracle for all original features") **การเปลี่ยน
default นี้คือการเบี่ยงเบนจาก oracle ไม่ใช่การแก้บั๊ก** ถ้าจะทำต้องผ่าน Extension
policy (`# EXTENSION: beyond oracle` พร้อมเหตุผล บันทึกใน docs/extensions.md)
ไม่ใช่แก้เงียบๆ

---

## 2. กรณี (ก) โค้ดตั้ง default เทียบกับ (ข) ข้อมูลที่เก็บไว้แล้วในไฟล์

กรณี (ก) คือรายการในข้อ 1 ด้านบน ส่วนกรณี (ข) — ตรวจสอบตรงๆ ไม่ใช่การเดา —
**พบว่าแทบไม่มีผลกระทบเลย**:

- `tests/golden/tables.json` และ `reference/tables.json`: ตรวจด้วยสคริปต์ Python
  จริง ทั้งสองไฟล์เก็บค่า `""` (สตริงว่าง) ให้ทุกแถว T/C อยู่แล้ว (20 แถวต่อไฟล์)
  **ไม่มีแถวใดได้รับผลกระทบเลย** เพราะ patch ใน `cli.py:135` (ข้อ 1) เป็นตัวสร้าง
  fixture เหล่านี้ตั้งแต่ต้น
- ไฟล์ `test_data/*.csv` ทั้ง 9 ไฟล์: grep หา `,T,CLOTHOID` และ `,C,CLOTHOID` —
  **ไม่พบสักแถวเดียว** `elements_output.csv` ก็ blank ค่านี้อยู่แล้ว (patch เดียวกัน)
  ส่วนไฟล์ format PI-table (`SettingOutTest.csv`, `SMT_TEST_CLOTHIOD.csv` ฯลฯ)
  ไม่มีแถว Type=T/C เลยตั้งแต่ต้น (เป็นแถว PI vertex คนละ schema กัน)
- `reference/vba/*.bas` และ `README.md`: ทุกจุดที่มี CLOTHOID เป็นแค่ comment
  อธิบาย column mapping (เช่น `col8=Transition(CLOTHOID/BLOSS/...)`,
  `blank = CLOTHOID`) ไม่ใช่แถวข้อมูลจริง
- `docs/SMT_CLI_Manual.md:87`, `docs/SMT_Python_Manual.md:90`: "ว่าง = CLOTHOID"
  อธิบายคอลัมน์ Transition ของ **PI-table input** (ใช้กับส่วน spiral Ls/LsIn/LsOut
  ของกลุ่มโค้งเท่านั้น) เป็นคนละเรื่องกับ internal representation ของ T/C ที่กำลัง
  พิจารณาอยู่ ไม่ได้รับผลกระทบจากการแก้ T/C
- **จุดที่เป็น "ข้อมูลเก็บไว้จริง" 2 จุดเดียวที่พบ ทั้งคู่อยู่ใน test source ไม่ใช่ fixture**:
  - `tests/test_alignment.py:329` — แถว input ทดสอบ literal
    `[0, 1000, 20000, 10000, 90.0, None, 'T', 'CLOTHOID']` (ไม่ได้ assert ค่านี้
    แค่เป็น input)
  - `tests/test_alignment.py:312-314` — **`test_make_element_trans_none_defaults_clothoid`**:
    สร้าง element `'T'` ด้วย `trans=None` แล้ว assert `el.transition == 'CLOTHOID'`
    **ทั้งชื่อ test และค่าที่ assert ตรงๆ** — นี่คือ test เดียวที่จะพังจริงถ้าเปลี่ยน default

---

## 3. ยืนยันว่าไม่มีจุดใดตรวจสอบค่า Transition ของ T/C อย่างมีนัยสำคัญ

grep `== 'CLOTHOID'` / `Case "CLOTHOID"` ทั่ว `src/smt/` และ `reference/vba/` —
**ไม่พบเลยสักจุดเดียว** พบแค่ 2 จุดเดิมคือ fallback check `Len(Trim(...))=0` ใน VBA
`_shape_integral`/`SMT_ShapeIntegral` ใช้ `Case Else` เป็น branch ของ CLOTHOID
(ไม่ใช่ `Case "CLOTHOID"` ที่ match ตรงๆ) หมายความว่าแม้แต่ fallback code path
ของ spiral ก็จะปฏิบัติกับสตริงที่ไม่รู้จักเหมือน CLOTHOID ทุกประการอยู่แล้ว รวมกับที่
T/C ไม่มีทางไปถึงโค้ดจุดนั้นเลย **สรุปได้ว่าค่า default ตัวอักษรจริงๆ ไม่มีผลต่อการ
คำนวณของ T/C เลยในทุก code path ที่มีอยู่ตอนนี้**

---

## 4. ผลตรวจสอบเพิ่มเติม — `test_spiral_trans_match` ไม่กระทบ

`tests/builders/test_alignment_builder.py:313-318`
(`test_spiral_trans_match`) กรองด้วย `if b_el.type in ('SPIN', 'SPOUT')` **อยู่แล้ว**
— ไม่ได้เทียบค่า transition ของ T/C เลย ไม่ว่าจะเปลี่ยน default T/C เป็นอะไร
test นี้และ golden fixture ก็ไม่ต้องแก้

---

## 5. ตัวเลือก placeholder ใหม่ ข้อดี/ข้อเสีย

| ตัวเลือก | ข้อดี | ข้อเสีย |
|---|---|---|
| `""` (สตริงว่าง) | ตรงกับที่ output จริงใช้อยู่แล้ว (via cli.py patch) | **ไม่ปลอดภัยสำหรับใช้เป็นค่าที่เก็บ/ป้อนกลับ** เพราะ trigger fallback เดิมกลับมาเป็น CLOTHOID เอง ทั้ง Python (`trans or 'CLOTHOID'` — falsy string) และ VBA (`Len(Trim(transStr))=0`) ทุกครั้งที่ re-parse ผ่าน `parse_alignment_table`/`SMT_SolveForward`/`SMT_SolveInverse` — ทำลายจุดประสงค์ของการเปลี่ยนเอง |
| `"N/A"` | คุ้นเคยในสเปรดชีตทั่วไป, ผ่าน fallback check ได้ (truthy) | อาจถูกอ่านผิดเป็น "not applicable" มากกว่า "ไม่ใช้กับ element ชนิดนี้" |
| `"-"` | เรียบง่าย ไม่รบกวนสายตาใน Excel | อาจดูเหมือนค่าที่หายไป/error มากกว่าตั้งใจ |
| `"NONE"` | ชัดเจนที่สุดว่า "ไม่มี transition" ผ่าน fallback check ได้ | ยาวกว่าตัวเลือกอื่นเล็กน้อย |

ทั้ง `"N/A"`/`"-"`/`"NONE"` เป็น truthy string ทั้งหมด จึงผ่าน fallback check ได้
โดยไม่ถูกแปลงกลับเป็น CLOTHOID ต่างจาก `""` ที่ต้องระวังเป็นพิเศษ

---

## 6. ประเด็นความเสี่ยงหลัก — การเบี่ยงเบนจาก oracle

ตามข้อ 1 การเปลี่ยน default ไม่ใช่การแก้บั๊ก แต่เป็นการเบี่ยงเบนจากพฤติกรรมของ
`reference/Alignment.gs` ที่ผ่านการยืนยันแล้ว (AllTests 45/45) ตามกฎ CLAUDE.md
Extension policy ต้องทำเครื่องหมาย `# EXTENSION: beyond oracle` พร้อมเหตุผล
และบันทึกใน `docs/extensions.md` ถ้าจะดำเนินการต่อ ไม่ใช่แก้เงียบๆ

---

## 7. ตรวจสอบเพิ่มเติม — export/dump utility อื่นที่อาจเขียนค่า Transition ดิบๆ ออกไป

grep `\.transition` ทั่วทั้ง `src/smt/` (ไม่จำกัดแค่ cli.py) พบทั้งหมด 7 จุดเท่านั้น:
- `alignment.py:271` — ใช้ภายในการคำนวณ (`_calculate_turning_angle_at` เรียก
  `_shape_integral`) ไม่ใช่ export
- `alignment.py:381` — ใช้ภายในการคำนวณ (เช็ค branch COSINE) ไม่ใช่ export
- `landxml.py:246,252,269,275` — ทั้ง 4 จุดอยู่ใน branch `el.type == 'SPIN'`
  และ `el.type == 'SPOUT'` เท่านั้น (ยืนยันแล้วก่อนหน้านี้ในรายงานนี้ว่า branch
  `el.type == 'T'`/`'C'` ใน landxml.py ไม่แตะ `el.transition` เลยแม้แต่บรรทัดเดียว
  — ปลอดภัยเชิงโครงสร้าง ไม่ใช่เพราะมี patch คอยดัก)
- `cli.py:135` — จุดเดียวที่เขียนออกไฟล์จริง มี patch blanking อยู่แล้ว

grep เพิ่มเติมใน `webhelpers.py` และ `check.py` (ฟังก์ชันช่วยอื่นที่อาจ export/dump
ตาราง element) หา `transition`/`el.type`/`for el in` — **ไม่พบการอ้างอิงใดๆ เลยทั้ง
สองไฟล์** ไม่มีการ export/dump element table ในไฟล์เหล่านี้

**สรุป: ตรวจสอบครบทั่วทั้ง `src/smt/` แล้ว ไม่พบ export/dump utility อื่นนอกเหนือจาก
`cli.py:135`'s `_run_build` ที่เขียนค่า `el.transition` ดิบๆ ออกไปให้คนอ่านโดยไม่ผ่าน
การป้องกัน** (`landxml.py` ปลอดภัยเชิงโครงสร้างเพราะ branch T/C ไม่แตะ field นี้เลย
ไม่ใช่เพราะมี patch คล้ายกัน) **ไม่มีจุดเสี่ยงอื่นที่ต้องพิจารณาเพิ่ม pattern เดียวกันในขณะนี้**
หากมีการเพิ่ม export/dump utility ใหม่ในอนาคตที่ serialize `Element` ทั้ง object
(ไม่ใช่แค่ field ที่เลือกเอง) ควรตรวจสอบจุดนั้นซ้ำตอนนั้น เพราะยังไม่มี test หรือ
lint rule ใดบังคับ pattern การ blank T/C ไว้เป็นมาตรฐานกลาง — เป็นแค่ convention
ที่ทำตรงจุดเดียวในโค้ดปัจจุบัน

---

## 8. ขอบเขตที่แนะนำ

**แนะนำ (ก) แก้แค่โค้ด ไม่แตะ fixture ใดๆ เลย — หรือพิจารณาไม่แก้เลยด้วยซ้ำ**

เหตุผล:
1. กรณี (ข) แทบไม่มีผลกระทบจริง (ข้อ 2) — fixture สะอาดอยู่แล้วเพราะมี patch
   `cli.py:135` คอยจัดการอยู่แล้วที่จุด export เดียวที่จำเป็น
2. ประสบการณ์ Phase 3 (`session_logs/investigate_phase3_golden_regen_scope.md`)
   ที่ regenerate golden fixture ด้วยเหตุผลอื่น พบว่าเกิด diff noise ในแถวที่ไม่
   เกี่ยวข้องจำนวนมากโดยไม่ได้ตั้งใจ — เป็นต้นทุนที่ไม่คุ้มค่าเมื่อไม่มี fixture ไหน
   ที่ต้องแก้ค่าจริงๆ ในกรณีนี้
3. การแก้ internal default คือการเบี่ยงเบนจาก oracle (ข้อ 6) ต้องผ่าน Extension
   policy เต็มรูปแบบ ทั้งที่ประโยชน์ที่ได้คือแค่ความสวยงามของ label ภายใน ไม่ได้แก้
   บั๊กหรือความเสี่ยงจริงใดๆ (ข้อ 3 ยืนยันแล้วว่าค่านี้ไม่มีผลต่อการคำนวณเลย)

**ทางเลือกที่บันทึกไว้แต่ไม่แนะนำ**: เปลี่ยน internal default จาก 'CLOTHOID' เป็น
placeholder ใหม่ (เช่น "NONE") พร้อมทำ Extension policy ให้ครบ (ทำเครื่องหมาย
`# EXTENSION: beyond oracle`, อัปเดต `docs/extensions.md`, แก้ test ที่ระบุใน
ข้อ 2 ทั้งชื่อและ assertion) — เป็นทางเลือกที่เป็นไปได้แต่ต้นทุน/ประโยชน์ไม่คุ้มกัน
ตามการประเมินนี้

ยังไม่มีการเขียนแผนแก้ใดๆ ในรอบนี้ตามคำสั่งของผู้ใช้ รายงานนี้ระบุแค่ข้อเท็จจริง
และข้อเสนอเท่านั้น
