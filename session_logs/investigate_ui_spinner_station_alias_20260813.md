# สืบสวน: UI spinner ค้าง "กำลังคำนวณ..." + ต้นตอ NaN station

**วันที่:** 2026-08-13
**สถานะ:** สืบสวนเสร็จ (โดย Claude Code + เพิ่มเติมโดย Claude Chat) ยังไม่ได้แก้ไฟล์ใดๆ

## สรุปห่วงโซ่ทั้งหมด (จาก Claude Code)

```
Sheet header "STATION" (คำเต็ม) ไม่ใช่ "STA" (ตัวย่อ)
  → GS_TableSplitter.js::parseHeader_() หา key ไม่เจอใน COL_ALIASES
    → colMap['sta'] = undefined
  → cell_(row, colMap, 'sta') คืน '' ทุกแถว drawing
  → parseFloat('') = NaN ทุกแถว (ไม่ใช่แค่จุดเดียว)
  → GS_CrossCheck.checkPoints() เรียก stationToCoord(elements, NaN, 0)
    แถวแรก → throw ทันที ('station NaN อยู่นอกแนวเส้นทาง')
  → runFullPipeline() ทั้งก้อนไม่ return เลย (แม้ exportElementsToSheet
    จะรันสำเร็จไปแล้วก่อนหน้า — เป็นเหตุผลที่ผลลัพธ์ element ครบสมบูรณ์
    แต่ตัว pipeline ยัง "ล้ม")
  → google.script.run เรียก onCalcFail() แทน onCalcDone()
  → onCalcFail() เรียก showError() ขึ้น banner ถูกต้อง แต่ไม่แตะ
    calcStatus.textContent เลย → ค้าง "กำลังคำนวณ..." ตลอดไป
```

**สรุป: เป็น 2 บั๊กที่แยกกันชัดเจน ไม่ใช่บั๊กเดียว**

## บั๊กที่ 1 — Column-alias gap: "STATION" ไม่รู้จัก (มีทั้ง Python และ GAS)

`GS_TableSplitter.js::COL_ALIASES` (บรรทัด 26-43) รู้จักแค่ `'sta'`/`'chainage'`
ไม่มี `'station'` เลย

**Claude Chat ตรวจเพิ่ม: `src/smt/builders/table_splitter.py::_COL_ALIASES`
(บรรทัด 20-37) มี gap เดียวกันเป๊ะ** — ไม่มี `'station'` เช่นกัน ยืนยันว่า
Python และ GAS sync กันถูกต้อง (ตรงตามที่ควรจะเป็น) แต่ **ทั้งคู่มีช่องโหว่
เดียวกัน** — ถ้าป้อน CSV/Sheet ที่ใช้ header คำเต็ม "STATION" เข้า Python
ก็จะเจอ NaN cascade แบบเดียวกันทันที ไม่ใช่ปัญหาเฉพาะ GAS

`table_splitter.py` **ไม่ใช่** protected function (ไม่อยู่ในลิสต์
`parse_pi_table`/`build_alignment_from_pi`/`check_against_drawing`) —
แก้ตรงได้เลย ไม่ต้องผ่านกระบวนการ Oracle correction exception

## บั๊กที่ 2 — UI ไม่เคลียร์ calcStatus เมื่อ error

`Index.html::onCalcFail()` (บรรทัด 388-395) เรียก `showError(err)` แต่ไม่มี
บรรทัดไหนแตะ `calcStatus.textContent` เลย — ต่างจาก `onCalcDone()` ที่อัปเดต
`calcStatus` ให้ตรงเสมอ **จะเกิดกับทุก error path ไม่ใช่แค่ NaN station**
เป็นบั๊กที่มีอยู่ก่อนงาน .gs sync แน่นอน ไม่เกี่ยวกับ #1/#2/#3

## แนวทางแก้ที่เสนอ (3 ส่วน แยกกันได้)

1. **เพิ่ม `'station': 'sta'` เข้า `COL_ALIASES`/`_COL_ALIASES`** ทั้ง
   `src/smt/builders/table_splitter.py` (Python) และ
   `reference/gsheet/GS_TableSplitter.gs` (GAS) — แก้ที่ต้นตอ ป้องกันทั้ง
   คลาสของปัญหานี้ในอนาคต ไม่ใช่แค่ไฟล์เดียวที่เจอวันนี้
2. **แก้ `onCalcFail()` ใน `Index.html`** ให้อัปเดต `calcStatus.textContent`
   ด้วย (เช่น `'คำนวณไม่สำเร็จ'` หรือข้อความคล้ายกัน) แทนที่จะปล่อยค้าง
3. **(ทางเลือก) แก้ header cell ในชีต `HOR_SMT_AL1` จริงจาก "STATION" เป็น
   "STA"** — ทำหรือไม่ทำก็ได้ถ้าข้อ 1 แก้แล้ว (เพราะ "STATION" จะรู้จักเอง)
   แต่ทำเร็วและช่วยให้สอดคล้องกับ template อื่นๆ ในโปรเจกต์

## คำถามก่อนวางแผนแก้จริง

1. เห็นด้วยกับขอบเขต 3 ส่วนข้างบนไหม หรืออยากตัดข้อไหนออก/เพิ่มอะไร?
2. ข้อ 1 (เพิ่ม alias) ควรรวม `'station'` เข้า `_NUMERIC_KEYS`/ตัวแปรที่
   เกี่ยวข้องอื่นๆ ด้วยไหม (Claude Chat จะตรวจให้ครบก่อนเขียนแผนจริง)
3. อยากให้แก้ชีต `HOR_SMT_AL1` (ข้อ 3) เป็นส่วนหนึ่งของงานนี้เลย หรือ
   CK1024 จะแก้เองภายหลัง?
