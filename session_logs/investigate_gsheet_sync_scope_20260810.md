# สืบสวนขอบเขต .gs sync สำหรับ #2 และ #3

**วันที่:** 2026-08-10
**สถานะ:** สืบสวนเสร็จ ยังไม่ได้แก้ไฟล์ใดๆ — รอวางแผน sync ต่อ

## สรุปสั้น — 2 เรื่องสำคัญที่เปลี่ยนลำดับความสำคัญของงานนี้

1. **บั๊ก #2/#3 กระทบเว็บแอปที่ทีมงานใช้งานจริงตอนนี้โดยตรง** — ไม่ใช่แค่
   ไฟล์ oracle สำหรับเทียบเฉยๆ ตามที่เข้าใจไว้ก่อนหน้า
2. **`reference/AlignmentBuilder.gs` (top-level, ไม่มี `gsheet/`) เป็นไฟล์ตาย**
   ไม่ใช่ไฟล์ที่ deploy จริง — เอกสาร #2 เดิม (`CLAUDE.md`/`docs/extensions.md`)
   ชี้ไปผิดไฟล์ ต้องแก้คำอธิบายด้วย ไม่ใช่แค่ sync โค้ด

## 1) มี clasp project 2 อัน คนละ scriptId กัน

| โฟลเดอร์ | scriptId | GS_PiTableParser.js? | GS_Pipeline.js/Index.html? | สถานะ |
|---|---|---|---|---|
| `D:\MyClasp_SMT_DEMO` | `1nZHagNeQJL-...` | ✅ มี | ✅ มี (webapp เต็มรูปแบบ) | **ตัวที่ deploy ใช้งานจริง** |
| `D:\MyClasp_verify` | `1KhIeWDq7VTZ...` | ❌ ไม่มี | ❌ ไม่มี | sandbox เก่า (ล่าสุด 18 ก.ค.) ไม่เกี่ยวกับ pipeline นี้ |

## 2) ไฟล์ที่ deploy จริง (`MyClasp_SMT_DEMO`) ตรงกับ git repo เป๊ะ (diff exit code 0)

```
GS_AlignmentBuilder.js (deploy) vs reference/gsheet/GS_AlignmentBuilder.gs (git) → เหมือนกันไบต์ต่อไบต์
GS_PiTableParser.js (deploy)    vs reference/gsheet/GS_PiTableParser.gs (git)    → เหมือนกันไบต์ต่อไบต์
```

แปลว่า `reference/gsheet/` ในโปรเจกต์ Python **คือกระจกสะท้อนของเว็บแอปจริงแบบ real-time** — แก้ที่นี่แล้ว push ผ่าน clasp เข้า `MyClasp_SMT_DEMO` จะอัปเดตเว็บแอปจริงทันที

## 3) `reference/AlignmentBuilder.gs` (top-level) คือไฟล์ตาย

- มีคอมมิตเดียวตั้งแต่สร้าง (`65d9cdb`) ไม่เคยถูกแก้อีกเลย
- ไม่มี EXT-001 (angle point) หรือ EXT-003 (spiral turning angle) — ฟีเจอร์ที่เพิ่มทีหลังทั้งคู่
- ไม่ตรงกับไฟล์ใน clasp folder ไหนเลย

ส่วน `reference/gsheet/GS_AlignmentBuilder.gs` (v2.0) มี EXT-001+EXT-003 ครบ ถูกแก้ต่อเนื่องล่าสุด (`8076529`) — **นี่คือไฟล์จริงที่ deploy อยู่**

## 4) บั๊กที่ยังไม่แก้ (ยืนยันจากเนื้อหาไฟล์จริงที่ deploy)

**`reference/gsheet/GS_AlignmentBuilder.gs` (#2):**
```javascript
// บรรทัด 165
var det = Math.sin(delta);        // ไม่มี guard สำหรับ δ≈0 หรือ δ≈π
// บรรทัด 174
var tanLen = WCB.distance2D(...)  // unsigned distance ไม่มี tan_len_signed/has_geometric_overlap
```

**`reference/gsheet/GS_PiTableParser.gs` (#3), `flushPending_()` บรรทัด 103-124:**
```javascript
function flushPending_() {
  if (pendingPi === null) return;   // ไม่เคลียร์ compoundArcs ก่อน return
  ...
}
```
orphan compound sub-row ก่อน PI ตัวแรกหรือหลัง EP ยังรั่วไปเกาะ PI อื่นแบบเงียบเหมือนเดิม

## 5) `runFullPipeline()` เรียกไฟล์ที่ยังไม่แก้ตรงๆ

`GS_Pipeline.js` บรรทัด 22-30:
```javascript
function runFullPipeline(fileId, tabName) {
  ...
  var vertices = GS_PiTableParser.parsePiTable(split.vertexRows);
  var built = GS_AlignmentBuilder.buildFromPI(vertices);
  ...
}
```
ฟังก์ชันนี้ export ผ่าน `doGet()` เป็นหน้าเว็บแอปจริง (`Index.html`) — **ทีมงานที่ใช้เว็บแอปนี้อยู่ตอนนี้ยังเจอบั๊ก #2/#3 อยู่จริง**

## 6) สถานะ clasp — พร้อม push

- `clasp --version` → 3.3.0 (ติดตั้งแล้ว)
- authenticated จริง (ยืนยันด้วย `clasp deployments` เรียก Google API สำเร็จ) — เห็น 6 deployments, ล่าสุด `@5 - "test1"` (มี `@HEAD` ด้วย)
- `clasp status` ใน `MyClasp_SMT_DEMO` → 15 tracked files ตรงกับที่เห็นจริง

## ประเด็นที่ต้องตัดสินใจก่อนวางแผน sync จริง

1. **`reference/AlignmentBuilder.gs` (ไฟล์ตาย)** — แก้ตามไปด้วย, ปล่อยไว้เป็นประวัติศาสตร์, หรือลบทิ้ง? และ `CLAUDE.md`/`docs/extensions.md` entry ของ #2 ที่ชี้ไปไฟล์นี้ต้องแก้คำอธิบายให้ชี้ไป `reference/gsheet/GS_AlignmentBuilder.gs` แทน
2. **`MyClasp_verify`** — ไม่ต้องแตะ (ยืนยันแล้วไม่เกี่ยวกับ production)
3. **`clasp push` เข้า `MyClasp_SMT_DEMO`** — กระทบเว็บแอปจริงทันทีที่ push ควร confirm แยกต่างหากเป็นขั้นตอนสุดท้ายของแผน ไม่รวมกับขั้นตอนแก้โค้ด/เทส
