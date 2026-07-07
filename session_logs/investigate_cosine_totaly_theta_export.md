# สืบสวน COSINE totalY/theta/tanShort ใน LandXML export — 2026-07-07

ผู้ใช้ขอให้สืบสวน (ยังไม่แก้โค้ด) ว่า known limitation ที่บันทึกไว้ตั้งแต่ EXT-003 —
theta/totalY/tanShort ของ COSINE (Civil 3D Sine Half-Wave) ใน LandXML export ยังใช้ค่า
ประมาณ ไม่ตรง Civil 3D จริง แม้ totalX จะแก้ไปแล้วก่อนหน้านี้ — มีสาเหตุจากอะไรแน่ชัด และ
ถ้าจะแก้ให้ตรง จะตกอยู่ในกรณีง่าย (แก้แค่ landxml.py เหมือน totalX) หรือกรณียาก (ต้องแก้ core
engine ที่กระทบทั้งระบบ)

สืบสวนผ่าน Explore agent (read-only) 2 ตัวคู่ขนาน + คำนวณ python จริงเพื่อยืนยันตัวเลข
ตัวเลขทั้งหมดตรงกับที่เคยบันทึกไว้ (0.00178° และ 0.01029°) ไม่มีจุดไหนต้องหยุดรายงาน
**นี่เป็นรายงานสืบสวนเท่านั้น ยังไม่มีการแก้โค้ดใดๆ**

---

## 1. `a` ที่ส่งเข้า `_sine_halfwave_point` ตอน d=length ไม่เท่ากับ 1 พอดี — ยืนยันแล้ว

`src/smt/alignment.py`:
- `_sine_halfwave_point` (บรรทัด 135-152) คำนวณ `a = x / big_x` ภายใน (บรรทัด 149)
  แล้วใช้ใน `theta = atan(big_x/r * (a/2 - sin(pi*a)/(2*pi)))` (บรรทัด 151)
- `calculate_point_on_element` กิ่ง SPIN (บรรทัด 292-297) เรียก
  `_sine_halfwave_point(d, big_x, r)` — เมื่อ `d = length` (ที่ `calculate_exit_state` ใช้จริง
  บรรทัด 336-338 `return calculate_point_on_element(el, el.sta_end - el.sta_start)`)
  จะได้ `x = length` ไม่ใช่ `x = big_x`
- ดังนั้น `a = length / big_x = L / X` **ไม่เท่ากับ 1 พอดี** เพราะ `X < L` เสมอ (จาก closed-form
  `X = L - 0.0226689447*L³/R²`) — กิ่ง SPOUT (บรรทัด 298-306) ก็ใช้ `x = length` เช่นกันสำหรับ
  `theta_total` ที่ครอบงำค่า theta ที่จุดออก
- `landxml.py` บรรทัด 236, 259: `theta_rad = _theta_rad(el.azimuth, exit_az)` โดย `exit_az` มาจาก
  `_exit_azimuth()` (บรรทัด 71-74) ซึ่งสำหรับ element สุดท้ายเรียก
  `calculate_exit_state(elements[-1]).azimuth` — เส้นทางเดียวกับข้อ (a=L/X) ข้างต้น ไม่ใช่ a=1

## 2. ยืนยันตัวเลขด้วย Python — ตรงกับที่บันทึกไว้เดิมทุกตัว

สูตรปิดที่พิสูจน์แล้วตรง Civil 3D (จาก `session_logs/investigate_sinehalfwave_formula.md`):
`X = L - 0.0226689447*L³/R²`, `theta_exact = atan(X/(2R))` (คือ a=1 พอดี),
`Y_exact = 0.14867881635766*X²/R`

ผลคำนวณจริง (`python3 -c`):

| กรณี | X (closed-form) | theta ปัจจุบัน (a=L/X) | theta จริง (a=1) | ส่วนต่าง |
|---|---|---|---|---|
| R=900, L=100 | 99.972014 | 3.1807182112° | 3.1789420269° | **0.0017762°** |
| R=250, L=50  | 49.954662  | 5.7157369848° | 5.7054491909° | **0.0102878°** |

ตรงกับตัวเลขที่เคยบันทึกไว้ใน `investigate_sinehalfwave_formula.md` บรรทัด 49-50 (0.00178°
และ 0.01029°) ทุกตัว — **ไม่มีจุดที่ต้องหยุดรายงาน**

`L - X` = 0.027986 ม. (R=900/L=100) และ 0.045338 ม. (R=250/L=50) — ตรงกับบันทึกเดิมเช่นกัน

## 3. theta ที่ export กับ azimuth ที่วาง element ถัดไป เป็นค่าเดียวกันจริง

`landxml.py::_exit_azimuth(i, elements)` (บรรทัด 71-74): ถ้าไม่ใช่ element สุดท้าย
return `elements[i+1].azimuth` ตรงๆ — คือค่าที่ `builders/alignment_builder.py::
build_alignment_from_pi` (บรรทัด 409-421) กำหนดไว้ตอน build จริง โดยบรรทัด 419-420
`state = calculate_exit_state(el); cur_n, cur_e, cur_az = state.n, state.e, state.azimuth`
แล้วบรรทัด 415 ส่ง `cur_az` (ของ element ก่อนหน้า) เป็น azimuth เริ่มต้นของ element ถัดไป

สรุป: **`theta` ที่ label ใน Spiral tag กับ azimuth ที่ใช้วาง element ถัดไปจริงในไฟล์เดียวกัน
มาจากตัวแปรเดียวกัน** (`calculate_exit_state(...).azimuth`) ทั้งฝั่ง internal chain (ทุก element
ที่ไม่ใช่ตัวสุดท้าย) และฝั่ง export (element สุดท้าย คำนวณตรงจาก `landxml.py:74`)

เพิ่มเติมที่ตรวจพบ (สำคัญต่อข้อ 4): แต่ละ Spiral tag ยังมี sub-tag `<End>` เป็นพิกัด N,E จริง
(`landxml.py:251-252, 274-275`) ที่คำนวณจาก `end_n, end_e` — พิกัดนี้มาจาก azimuth เดียวกันกับ
theta (a=L/X, ค่าประมาณปัจจุบัน) ไม่ใช่คนละค่า

## 4. ถ้าแก้ theta ให้ตรง Civil 3D เฉพาะตอน export (แบบเดียวกับ totalX) จะเกิดอะไร

**จะเกิดความไม่สอดคล้องภายในไฟล์เดียวกันจริง ต่างจากกรณี totalX** เพราะเหตุผลเชิงโครงสร้าง:

- totalX เป็นตัวเลขบรรยาย (descriptive) ของ element เดียว ไม่มีใครใน chain ใช้มันวาง element
  ถัดไป — การ override เฉพาะตอน export จึงปลอดภัย (ไม่มีอะไรอื่นในไฟล์ที่ต้อง "ตรงกับ" totalX)
- แต่ theta **คือค่าเดียวกับ azimuth ที่ใช้วาง element ถัดไปจริง** (ข้อ 3) — ถ้า override
  เฉพาะค่า `theta=` attribute ที่ export โดยไม่แตะ `calculate_exit_state`/chain จริง จะได้ไฟล์ที่:
  1. `theta` บอกมุมเบี่ยง 3.178942° (ค่าถูกต้อง) แต่ **พิกัด `<End>`** ของ Spiral tag เดียวกันนั้น
     ยังคำนวณจาก azimuth เดิม (มุมเบี่ยงจริง 3.180718°) — ตัวเลขสองค่าใน tag เดียวกันขัดแย้งกันเอง
  2. **`dirStart`/พิกัดเริ่มต้นของ element ถัดไป** ในไฟล์เดียวกันก็ยังวางตามมุมเบี่ยงเดิม
     (3.180718°) เพราะ `elements[i+1].azimuth` ถูกกำหนดไว้แล้วตอน build (ก่อน export) — ไม่ได้
     recompute จาก theta ที่แก้ใหม่ — เท่ากับว่าไฟล์ประกาศ theta หนึ่งค่า แต่ใช้จริงอีกค่าหนึ่ง
     ในการวาง element ถัดไป
  3. `tanLong = totalX - totalY/tan(theta_rad)` และ `tanShort = totalY/sin(theta_rad)`
     (`landxml.py:113-114`) — ถ้าสลับเฉพาะ `theta_rad` เป็นค่าจริง แต่ `total_y` ยัง approximation
     เดิม (ตามที่บันทึกไว้ใน docstring `landxml.py:99-101` ว่า totalY ยังใช้ d=length approximation)
     จะได้สูตรผสมระหว่างค่าที่พิสูจน์แล้ว (theta) กับค่าที่ยังไม่พิสูจน์ (totalY) เป็นคู่ที่ไม่เคย
     ยืนยันกับ Civil 3D จริง — ground truth เดิม (บรรทัด 20-21, 24-25 ใน
     `investigate_sinehalfwave_formula.md`) ยืนยัน theta กับ totalY เป็น**คู่ที่มาจาก a เดียวกัน
     เสมอ** (ทั้งคู่ a=1 พอดี) ไม่เคยพิสูจน์การผสม a ต่างกันระหว่างสองค่านี้

ตัวอย่างตัวเลขจริง (R=900, L=100, สมมติ entry azimuth = 0° เพื่อความง่าย):
ถ้า override เฉพาะ `theta=` เป็น 3.178942° แต่ `<End>` coordinate และ dirStart ของ element ถัดไป
ยังคำนวณจาก azimuth 3.180718° → ผู้บริโภคไฟล์ (เช่น Civil 3D อ่านกลับ) ที่คำนวณทิศทางปลาย spiral
จาก theta จะได้ 3.178942° แต่ถ้าคำนวณจากพิกัด Start→End ของ tag เดียวกันจะได้ทิศทางที่สอดคล้องกับ
3.180718° แทน — ไฟล์ขัดแย้งในตัวเอง (self-inconsistent)

## 5. ไม่มี ground truth จุดกลางโค้ง — ผลกระทบถ้าแก้เฉพาะจุดปลาย

จาก `investigate_sinehalfwave_formula.md` บรรทัด 28-31 และ 47-51: Civil 3D ground truth
ที่มีอยู่ทั้งหมดยืนยันแค่ค่าที่ **d=L (จุดปลาย element) เท่านั้น** ไม่มีจุดกลางโค้ง (d<L) ยืนยันเลย
สูตรปัจจุบันใช้ `a = d/X` (สมมติฐาน x≈s) ต่อเนื่องตลอดทั้งเส้นตั้งแต่ d=0 ถึง d=L

ถ้าแก้ core engine ให้ที่ `d=length` พอดีใช้ `a=1` (ค่า exact) แต่จุดกลาง (d<L) ยังใช้ `a=d/X`
(ค่าประมาณเดิม) จะเกิด **jump discontinuity ตรงขอบ**: ลิมิตของ theta(d) เมื่อ d→L⁻ จะเข้าใกล้
theta ที่ a=L/X (ค่าประมาณ, 3.180718°) ไม่ใช่ a=1 (ค่าจริง, 3.178942°) — แล้วพอ d=L พอดีค่าจะ
กระโดดไปอีกค่าหนึ่งทันที ไม่ต่อเนื่อง

นี่คือรูปแบบเดียวกับที่ totalX เคยทำมาแล้ว (totalX override เฉพาะ d=length ก็มี discontinuity
แบบเดียวกัน) — ที่ยอมรับได้สำหรับ totalX เพราะไม่มีใคร sample จุดกลางแล้วเทียบความต่อเนื่องกับ
totalX จุดปลาย (มันเป็นแค่ตัวเลขสรุปทั้ง element) แต่สำหรับ theta/azimuth **ความต่อเนื่องมีผลจริง**
เพราะ chain ทั้งเส้นพึ่งพา exit azimuth ต่อกันเป็นทอดๆ (ข้อ 3-4)

## 6. สรุป: กรณีง่ายหรือกรณียาก

**ตกอยู่ในกรณียาก — ต้องแก้ core engine ไม่ใช่แค่ landxml.py**

เหตุผล:
- totalX แก้ได้แค่ที่ export boundary เพราะไม่มีอะไรอื่นใน chain พึ่งพามัน (ตัวเลขบรรยายเดี่ยวๆ)
- theta/exit-azimuth **เป็นกลไกหลักของ chain continuity เอง** — `build_alignment_from_pi`
  (builder) และ `landxml.py` (export) เรียก `calculate_exit_state` ตัวเดียวกัน ถ้าแก้แค่ตอน
  export โดยไม่แก้ `calculate_point_on_element`/`calculate_exit_state` ใน `alignment.py` จะได้
  ไฟล์ที่ theta ไม่ตรงกับพิกัด End ของ tag เดียวกัน และไม่ตรงกับ azimuth จริงที่ element ถัดไปใช้
  (ข้อ 4) — เป็น bug ใหม่ที่หนักกว่าที่มีอยู่ตอนนี้
- ถ้าจะแก้ให้ถูกจริง ต้องแก้ `calculate_point_on_element`/`calculate_exit_state` ใน core engine
  ให้ที่ d=length ใช้ a=1 (x=big_x) แทน a=L/X (x=length) — ซึ่งจะ:
  1. เปลี่ยนค่า exit azimuth ที่ builder ใช้จริงสำหรับทุก element ถัดจาก COSINE spiral ใน
     alignment ใดๆ ก็ตามที่มี COSINE (กระทบทุกอย่างที่ต่อจากจุดนั้น: station-to-coordinate,
     coordinate-to-station, cross-check)
  2. ต้อง regenerate `tests/golden/tables.json` และ `reference/tables.json` ใหม่ (เช่นเดียวกับ
     ที่เคยทำตอนแก้ `_build_curve_sub_elements` — ดู
     `session_logs/investigate_cosine_builder_mismatch_20260705.md`)
  3. ต้องอัปเดต `SMT_Core.bas`/`SMT_Alignment.bas` ให้ตรงกันในรอบเดียวกัน (กฎ CLAUDE.md 4.3)
  4. ยังคงเหลือปัญหา discontinuity ที่ขอบ d=length เว้นแต่จะมีข้อมูล ground truth จุดกลางมา
     ยืนยันสูตร x(s) ตลอดทั้งเส้น (ซึ่งยังไม่มี ตามข้อ 5) — จึงยังต้องตัดสินใจเชิงนโยบายเพิ่มเติม
     ว่าจะยอมรับ discontinuity ที่ขอบ (เหมือน totalX) หรือรอข้อมูลจุดกลางก่อน

**คำแนะนำ (ยังไม่ใช่แผนแก้ เป็นแค่ข้อสังเกตปิดท้าย)**: การแก้ totalX ที่ผ่านมาปลอดภัยเพราะเป็น
descriptive field เดี่ยว ส่วน theta/totalY/tanShort ผูกกับ chain continuity โดยตรง จึงไม่ควรทำ
แบบเดียวกัน (export-boundary-only) — ถ้าต้องการแก้จริง ควรเปิดเป็นงานแยกที่วางแผนแก้ core engine
พร้อม regenerate fixtures และอัปเดต VBA ตามกฎ ไม่ใช่ patch จุดเดียวใน landxml.py
