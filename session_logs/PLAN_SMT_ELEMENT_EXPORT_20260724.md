# แผนงาน — Export ข้อมูล Element ของแนวเส้นทาง (อัปเดต 2026-07-24 หลังยืนยันรายละเอียด)

**อ่านไฟล์นี้ก่อนเริ่ม session ใหม่ — เวอร์ชันนี้แทนที่ฉบับก่อนหน้า มีรายละเอียด
ที่ยืนยันแล้วครบ + แบ่ง session ทำงานไว้ให้แล้ว**

---

## 1. สิ่งที่ยืนยันแล้ว (จากคำตอบของ CK1024)

### 1.1 ปลายทาง export
Export เป็น **tab ใหม่ในสเปรดชีตเดียวกับที่ข้อมูล alignment อยู่** (ไม่ใช่ไฟล์แยก)

**ข้อเสนอแนะทางเทคนิค**: แทนที่จะใช้ `SpreadsheetApp.getActiveSpreadsheet()`
(ซึ่งจะทำงานถูกก็ต่อเมื่อรันจากภายใน Apps Script ที่เปิดจากสเปรดชีตนั้นโดยตรง
เท่านั้น) แนะนำให้ใช้ **ตัวแปร `ss` ตัวเดียวกับที่เปิดด้วย `SpreadsheetApp.openById(...)`
ตอนอ่านข้อมูลเข้ามา** แล้วเรียก `ss.insertSheet('Elements')` บนตัวนั้นเลย —
ได้ผลเหมือนกัน (เขียนกลับลงไฟล์เดียวกับที่ข้อมูลมา) แต่ทำงานถูกต้องแน่นอนไม่ว่า
จะรันจากที่ไหน (web editor, trigger, หรือในอนาคตเวลาต่อ web app ที่ต้องรองรับ
หลาย alignment/หลายไฟล์พร้อมกัน) — robust กว่าและตรงกับ design เดิมที่วางไว้
(หลาย alignment แต่ละอันเป็นไฟล์สเปรดชีตแยกกัน)

### 1.2 ตาราง output — 2 ตารางแยกกัน

**ตารางที่ 1 — Element table (สำหรับคำนวณ)**
ตารางเดียวกับที่ Python core สร้างอยู่แล้ว (โครงสร้าง/คอลัมน์ต้องไปดูจากซอร์สจริง
ก่อน — ยังไม่ทราบคอลัมน์ที่แน่ชัด ดูหัวข้อ 3 ขั้นตอนที่ 1)

**ตารางที่ 2 — Cross-check comparison table**
เปรียบเทียบค่าที่จุดต่างๆ ระหว่างค่าที่คำนวณได้กับค่าที่ลาก/สำรวจจริง:
- จุด PC: ผลต่าง N, E
- จุด PI: ผลต่าง N, E, RADIUS
- จุด TS, SC, CS, ST: ผลต่าง (N, E)
- ผลต่างค่ารัศมีโค้ง (radius) และมุม deflection ด้วย

*(ต้องเช็คว่า `check_against_drawing()` ที่มีอยู่แล้วคำนวณ delta พวกนี้อยู่แล้ว
บางส่วนหรือไม่ หรือต้องเขียนชั้น comparison ใหม่ทั้งหมด — ดูหัวข้อ 3 ขั้นตอนที่ 1)*

### 1.3 ขอบเขตการ export
Export ทีละ 1 alignment (ไม่ต้องรองรับหลาย alignment พร้อมกันตอนนี้)

### 1.4 ยืนยัน: รองรับตารางดิบ 2 รูปแบบ — **ได้ทั้งคู่ครับ ไม่ต้องแก้โค้ดเพิ่มที่ชั้น split**

คำถามที่ถาม: ตารางดิบที่ทำเสร็จแล้ว (`GS_TableSplitter.gs`) รองรับทั้ง
(1) ตารางเต็ม (มีทุกจุด PC/PI/PT หรือ TS/SC/PI/CS/ST + RADIUS + SPIRAL LENGTH +
TRANSITION TYPE) และ (2) ตารางย่อ (มีแค่ PI + RADIUS + SPIRAL LENGTH +
TRANSITION TYPE ไม่มีจุดที่ลากไว้เลย) ได้หรือไม่

**คำตอบ: ได้ทั้งคู่ครับ — สถาปัตยกรรมเดิมออกแบบมารองรับอยู่แล้ว**

เหตุผลเชิงเทคนิค:
- `split_mixed_alignment_table()` (และ `GS_TableSplitter.gs` ที่พอร์ตแล้ว) แค่
  แยกแถวตาม pattern ของ POINT: ถ้าตรง `^(BP|PI-\d+|EP)$` หรือว่างเปล่า → เข้า
  `vertexRows` / ถ้าไม่ตรง (เช่น PC/PT/TS/SC/CS/ST) → เข้า `drawing`
- **กรณี (2) ตารางย่อ**: ถ้าไม่มีแถว PC/PT/TS/SC/CS/ST เลย ทุกแถวจะตรงเงื่อนไข
  vertex หมด → `vertexRows` มีข้อมูลครบ, `drawing` จะเป็น **array ว่างเปล่า
  (`[]`)** เฉยๆ ไม่ error อะไร
- `build_alignment_from_pi()` (และ `buildFromPI` ฝั่ง GAS) **คำนวณ element
  ทั้งหมดจาก PI + RADIUS + SPIRAL LENGTH + TRANSITION TYPE อยู่แล้วเป็นหลัก** —
  นี่คือหน้าที่หลักของฟังก์ชันนี้ (หา TS/SC/CS/ST ที่ควรจะอยู่ตรงไหนจาก
  เรขาคณิตล้วนๆ) ไม่ได้ต้องพึ่งจุดที่ลากไว้ (`drawing`) เลยในการคำนวณหลัก
- `drawing` (จุดที่ลากไว้จากแบบ) ใช้แค่ตอน **cross-check** (ตารางที่ 2) เพื่อ
  เทียบว่าที่ลากไว้ตรงกับที่คำนวณได้แค่ไหน — ถ้าไม่มีข้อมูล `drawing` เลย
  (กรณี 2) ก็แค่ **ข้ามขั้นตอน cross-check ไปเฉยๆ** (ไม่มีอะไรให้เทียบ) แต่
  ตารางที่ 1 (element ที่คำนวณได้) ยังคำนวณและ export ได้ตามปกติ

**สรุป**: กรณี (1) ได้ทั้งตารางที่ 1 และตารางที่ 2 / กรณี (2) ได้แค่ตารางที่ 1
(ตารางที่ 2 จะว่างเปล่าเพราะไม่มีอะไรให้เทียบ) — ไม่ต้องแก้โค้ดที่มีอยู่แล้วเลย
เพื่อรองรับทั้งสองกรณีนี้ สถาปัตยกรรมรองรับอยู่แล้วโดยธรรมชาติ

---

## 2. Pipeline เต็มที่ต้องต่อให้ครบ

```
ตารางดิบ (mixed หรือ PI-only)
   │
   ├─ split_mixed_alignment_table()   ✅ พอร์ตแล้ว (GS_TableSplitter.gs)
   ▼
vertexRows (string) + drawing (อาจว่างเปล่าถ้าเป็นกรณี PI-only)
   │
   ├─ parse_pi_table()                ❌ ยังไม่พอร์ต — งานหลักของ Session 2
   ▼
vertices (object พร้อมพิกัด/รัศมี/spiral ที่ parse แล้ว)
   │
   ├─ build_alignment_from_pi()       ✅ พอร์ตแล้ว (buildFromPI, verify แล้ว)
   ▼
alignment object (ครบทุก element คำนวณจบ)
   │
   ├─ flatten เป็นตาราง element        ❌ Session 4 — ตารางที่ 1
   ├─ check_against_drawing() + เทียบ  ❌ Session 5 — ตารางที่ 2 (ถ้ามี drawing)
   │  แบบ point-by-point delta
   ▼
เขียนลง Sheet tab ใหม่ (2 tabs: element table, cross-check table)
```

---

## 3. แบ่งงานเป็น Session (Plan-Review-Approve ทุก session เหมือนเดิม)

### Session A — สำรวจ (ไม่แก้โค้ดอะไรเลย แค่อ่าน)
- อ่าน `src/smt/builders/alignment_builder.py` เต็มไฟล์ (`parse_pi_table`,
  `build_alignment_from_pi`, `check_against_drawing`) เพื่อรู้ signature/logic
  จริงก่อนพอร์ต
- หา logic export element ที่มีอยู่แล้ว (ค้นคำว่า "element", "export", "flatten"
  ใน `src/smt/`) — ไฟล์ `elements_for_excel.csv` ที่เป็น untracked อยู่ในเครื่อง
  น่าจะมาจากโค้ดส่วนไหน ต้องหาให้เจอ เพื่อรู้คอลัมน์ตารางที่ 1 ที่แน่ชัด
- เช็คว่า `check_against_drawing()` มี logic คำนวณ delta แบบ N/E/radius/deflection
  รายจุดอยู่แล้วหรือไม่ (หรือมีแค่ gap_m รวมๆ ต้องเขียนชั้นเทียบใหม่)
- **Output ของ session นี้**: สรุปคอลัมน์ที่แน่ชัดของตารางที่ 1 และ 2 มาให้ตรวจ
  ก่อนเริ่มเขียนโค้ดจริง (อาจต้องถามคุณเพิ่มถ้ายังไม่ชัด)

### Session B — พอร์ต `parse_pi_table()` เป็น GAS
- ตามกระบวนการเดียวกับ `GS_TableSplitter.gs` ทุกขั้น: อ่านซอร์สจริง → เขียน
  draft → verify ด้วย Node.js เทียบ Python (ทั้งกรณีตารางเต็มและ PI-only) →
  อนุมัติ → สร้างไฟล์จริงใน repo → copy ไป clasp folder → verify กับ Sheet จริง
  → commit → push

### Session C — ต่อ pipeline เต็ม (split → parse → build)
- เขียนฟังก์ชันทดสอบที่เรียกครบ 3 ขั้น เทียบผลลัพธ์ alignment object กับ Python
  ทั้งกรณีตารางเต็มและ PI-only

### Session D — Export ตารางที่ 1 (element table)
- เขียนฟังก์ชัน flatten alignment object → เขียนลง Sheet tab ใหม่ (ผ่าน `ss`
  เดียวกับที่เปิดข้อมูลมา ตามข้อ 1.1)
- Verify คอลัมน์/ค่าตรงกับ Python

### Session E — Export ตารางที่ 2 (cross-check comparison table)
- เขียน/ต่อยอด logic เทียบ point-by-point delta (N, E, radius, deflection) ที่
  PC/PI/TS/SC/CS/ST
- เขียนลง Sheet tab ที่สอง
- Verify กับ Python (ถ้า Python มี logic เทียบแบบนี้อยู่แล้ว) หรือคำนวณ
  เองแล้วยืนยันด้วยมือสำหรับ 1-2 จุดก่อน

*(หมายเหตุ: จำนวน session ที่แบ่งไว้นี้เป็นแค่แนวทาง ปรับได้ตามหน้างานจริง —
เช่น Session A อาจเจอว่า export logic มีอยู่แล้วเกือบสมบูรณ์ ทำให้ Session D/E
เร็วขึ้นมาก หรือตรงกันข้าม)*

### Session F — หน้าเว็บจริง (doGet()+HTML) — เพิ่มเข้ามาหลังคุยกัน 2026-07-25

หลัง Session D/E จบ (engine คำนวณ+เปรียบเทียบพิสูจน์ถูกต้องหมดแล้ว ผลอยู่ใน
Sheet tab) ค่อยห่อเป็นหน้าเว็บจริงที่กรอกฟอร์ม/กดเลือกได้ (ไอเดีย 3.6.1 เดิม
ตั้งแต่ต้นโปรเจกต์ ที่เลื่อนไว้ก่อนตอนนั้น):
- `doGet()` + HTML แบบ cascade: เลือกโฟลเดอร์ → เลือกไฟล์ → เลือก alignment
- ปุ่ม "คำนวณ" เรียก pipeline เต็ม (split→parse→build→export) ที่ verify แล้ว
- แสดงผลตารางที่ 1/2 ในหน้าเว็บ (หรือลิงก์ไปที่ Sheet tab ที่เพิ่งเขียน)

เหตุผลที่ทำทีหลัง ไม่ทำพร้อมกับ D/E: ห่อ UI ทับ engine ที่ยัง verify ไม่เสร็จ
เสี่ยงต้องแก้ทั้ง UI และ engine พร้อมกันถ้าเจอบั๊กตอนทดสอบ — ทำ engine ให้ถูก
100% ก่อน (D/E) แล้วค่อยห่อ UI ทีหลังจะปลอดภัยกว่า

---

## 4. ข้อความสำหรับเริ่ม session ใหม่

```
นี่คือแผนงาน element export ของโปรเจกต์ SMT ฉบับอัปเดต (แนบไฟล์
PLAN_SMT_ELEMENT_EXPORT_20260724.md) — รายละเอียด requirement ยืนยันครบแล้ว
(หัวข้อ 1) แบ่งงานเป็น session A-E ไว้แล้ว (หัวข้อ 3) เริ่มจาก Session A
(สำรวจ Python core หาโครงสร้าง element/export ที่มีอยู่แล้ว ไม่แก้โค้ดอะไร)
ก่อนครับ
```
