# DRAFT_plan_session_F3_cascade_ui.md

**สถานะ: ร่างรอตรวจ (Plan) — ยังไม่ส่งให้ Claude Code เขียนไฟล์จริง**
**เขียน 2026-07-28 หลังคุยสเปคกับ CK1024 ในหัวข้อ 2.2 ของ handoff F.3**

---

## 1. เป้าหมาย F.3

สร้าง `doGet()` + หน้าเว็บ HTML แสดง cascade dropdown 3 ชั้น
(หมวด → ไฟล์ Google Sheets → alignment/tab) โดยเรียกใช้ backend functions
ที่มีอยู่แล้วจาก Session F.2 (`GS_DriveWalker.gs`) **ไม่แตะ pipeline คำนวณ
เลย** — งานนั้นเป็นของ F.4

---

## 2. สเปคที่ยืนยันแล้ว (คุยกับ CK1024, 2026-07-28)

1. **Dropdown ทั้ง 3 ชั้นแสดงอยู่บนหน้าจอตลอดเวลา** — ชั้นที่ยังไม่มีข้อมูล
   (รอ parent เลือกก่อน หรือรอ `google.script.run` ตอบกลับ) จะ `disabled`
   พร้อมข้อความ placeholder ในตัว dropdown เอง (ไม่ซ่อน/ไม่เผยทีละชั้น)
2. **หมวดที่ไม่มีไฟล์** แสดงทั้ง 2 อย่างพร้อมกัน: (ก) dropdown ชั้นไฟล์
   เปลี่ยนเป็น option เดียว disabled ข้อความ "ไม่มีไฟล์ในหมวดนี้" และ
   (ข) มีข้อความเตือนแยกต่างหากใต้ dropdown นั้น
3. **ขอบเขต F.3 = UI cascade อย่างเดียว** — แยกจาก F.4 (เชื่อมปุ่ม
   "คำนวณ" กับ pipeline จริง) ตามแผนเดิม ปุ่ม "คำนวณ" ปรากฏบนหน้าจอแต่
   `disabled` ถาวรใน F.3
4. **`doGet()` ใช้ `HtmlService.createHtmlOutputFromFile()` ไฟล์เดียว**
   (HTML+CSS+JS รวมกันในไฟล์เดียว) ไม่ใช้ `createTemplateFromFile()` —
   เพราะไม่มีความจำเป็นต้องฉีดค่าจาก server เข้า HTML ตอน render หน้าแรก
   (ข้อมูลทั้งหมดมาทาง `google.script.run` หลังโหลดหน้าเสร็จ)

---

## 3. ไฟล์ที่จะสร้าง/แก้ไข

| ไฟล์ | การเปลี่ยนแปลง |
|---|---|
| `Index.html` (ใหม่) | HTML+CSS+JS ทั้งหมดของหน้า cascade UI |
| `code.js` (แก้ไข) | เพิ่มฟังก์ชัน `doGet()` เดียว |

ไม่แตะไฟล์ engine/backend ใดๆ (`GS_DriveWalker.gs` ของ F.2 ใช้ตามเดิม
ไม่ต้องแก้)

---

## 4. `doGet()` (ใน `code.js`)

```javascript
function doGet() {
  return HtmlService.createHtmlOutputFromFile('Index')
    .setTitle('SMT — เลือกข้อมูล Alignment');
}
```

---

## 5. โครงสร้าง `Index.html`

- 3 `<select>`: `#catSelect` (หมวด) / `#fileSelect` (ไฟล์) / `#tabSelect`
  (alignment)
- ชั้นแรก (`#catSelect`) โหลดทันทีตอนเปิดหน้า (แสดง "กำลังโหลด..."
  ระหว่างรอ) ชั้นที่ 2-3 เริ่มต้นเป็น disabled พร้อม placeholder
  "-- เลือก...ก่อน --"
- ปุ่ม `#calcBtn` "คำนวณ" — แสดงตลอด `disabled` ถาวร มีข้อความกำกับใต้ปุ่ม
  ว่าจะเชื่อมจริงใน F.4

---

## 6. JS flow (client-side)

1. `window.onload` →
   `google.script.run.withSuccessHandler(populateCategories).withFailureHandler(showError).listCategoryFolders()`
2. `catSelect.onchange` → เคลียร์ `fileSelect`/`tabSelect` กลับเป็น
   disabled+loading ก่อน แล้ว
   `google.script.run.withSuccessHandler(populateFiles).withFailureHandler(showError).listFilesInFolder(folderId)`
   - ผลลัพธ์ว่าง → `fileSelect` เป็น option เดียว disabled "ไม่มีไฟล์ใน
     หมวดนี้" + โชว์ข้อความเตือนแยกใต้ dropdown (ตามข้อ 2.2)
3. `fileSelect.onchange` → เคลียร์ `tabSelect` กลับเป็น disabled+loading
   แล้ว
   `google.script.run.withSuccessHandler(populateTabs).withFailureHandler(showError).listAlignmentTabsInFile(fileId)`
   - ผลลัพธ์ว่าง (ไม่ควรเกิดปกติ แต่เผื่อไว้) → จัดการแบบเดียวกับข้อ 2
4. ไม่มี `tabSelect.onchange` handler พิเศษใน F.3 — แค่เก็บค่าที่เลือกไว้
   รอ F.4 มาต่อปุ่มคำนวณ

## 7. Error handling

- ฟังก์ชันกลาง `showError(err)` — ถ้า `google.script.run` fail (เช่น
  permission หลุด, network) ให้แสดงข้อความ error แบบทั่วไป ไม่ให้หน้าจอ
  ค้างเงียบๆ โดยไม่มีอะไรบอกผู้ใช้ — ยังไม่ต้อง handle รายละเอียดเจาะจง
  ทุก error type ใน F.3

---

## 8. การทดสอบ

- Apps Script ไม่มีทาง unit-test HTML/JS ฝั่ง client ได้ (ต้องรันจริงใน
  เบราว์เซอร์เท่านั้น)
- ทดสอบผ่าน "Test deployments" ในตัว editor (ยังไม่ deploy จริงถาวร —
  นั่นคือขอบเขตของ F.5) เปิด URL ทดสอบแล้วไล่ manual:
  - หมวดที่มีข้อมูลจริง (`001_Hor_Align`) → ต้องไล่ครบ 3 ชั้นจนถึง
    alignment ได้
  - หมวดว่าง (อีก 7 หมวด) → ต้องเห็นข้อความ "ไม่มีไฟล์" ครบทั้ง 2 จุด
    ตามข้อ 2

---

## 9. ขอบเขตที่ไม่ทำใน F.3 (ย้ำกันสับสน)

- ไม่เชื่อมปุ่ม "คำนวณ" กับ pipeline จริง (F.4)
- ไม่ deploy เป็น production web app (F.5)
- ไม่มี automated test อัตโนมัติ (ข้อจำกัดของ Apps Script HtmlService)

---

## 10. ข้อความเริ่ม session ถัดไป (ถ้าจบ F.3 แล้วยังไม่ได้ทำ F.4 ต่อ)

```
นี่คือ PROJECT_STATE.md ล่าสุด — ทำ Session F.4 ต่อจาก F.3 ที่เสร็จแล้ว
(เชื่อมปุ่ม "คำนวณ" ใน Index.html เข้ากับ pipeline เต็ม
split→parse→build→export ตามที่ยืนยันไว้ใน PROJECT_STATE.md §6)
```
