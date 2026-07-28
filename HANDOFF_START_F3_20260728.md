# HANDOFF — เริ่ม Session F.3 ในแชทใหม่
**เขียน 2026-07-28 — ต่อจาก Session F.1-F.2 ที่ปิดงานสมบูรณ์แล้ว**

---

## 0. บริบทของ handoff นี้

Session F.1 และ F.2 เสร็จสมบูรณ์ครบทั้งโค้ด (feat commits) และเอกสาร (docs
commits) push ขึ้น `origin/main` แล้วทั้งคู่ (HEAD ปัจจุบัน `9e5e608` — ดู
commit hash เต็มใน `PROJECT_STATE.md` §6) — ปิดแชทนี้ไว้เพราะเริ่มกังวลเรื่อง
token budget ไม่ใช่เพราะติดปัญหาอะไร

**ต่างจาก handoff ของ F.1**: รอบนั้นมีสเปคละเอียดพร้อมตั้งแต่ก่อนเริ่มแชท
แต่ **F.3 ยังไม่มีสเปคละเอียดเลย** — มีแค่แนวคิดกว้างๆ ที่ยืนยันไว้ใน
`PROJECT_STATE.md` §6 ("Session F — ดีไซน์ที่ยืนยันแล้ว" ข้อ 1-3) **งานแรก
ของแชทใหม่คือคุยสเปค F.3 กับ CK1024 ให้ชัดก่อน ไม่ใช่เริ่มเขียนโค้ดทันที**
คุยเป็นภาษาง่ายๆ ทีละข้อ ไม่ต้องยัดศัพท์เทคนิค — CK1024 พึ่งพา Claude Chat
เป็นที่ปรึกษาหลักด้านการออกแบบเชิงเทคนิค แต่การตัดสินใจเรื่องการใช้งานจริง
ในสนามยังต้องรอฟังจากเขาเสมอ

**สิ่งที่ต้องอัปโหลดในแชทใหม่**: 5 ไฟล์ — `PROJECT_STATE.md`,
`DEPENDENCY_MAP.md`, `BUNDLE_gsheet.md` (เวอร์ชันใหม่ 9 ไฟล์ รวม
`GS_DriveWalker.gs` แล้ว), `BUNDLE_python_core.md` (ไม่มีอะไรเปลี่ยน ใช้ตัว
เดิมได้), และไฟล์ handoff นี้

**หมายเหตุ**: Claude Chat มีบันทึกความจำที่โหลดอัตโนมัติเสมอไม่ว่าจะอัปโหลด
ไฟล์อะไรก็ตาม — มีรายละเอียดครบทั้งเหตุผลของทุกการตัดสินใจและบทเรียนที่เจอ
มาตลอด Session A-F.2 ไฟล์ 5 ไฟล์นี้เสริมแค่ "โค้ดจริงหน้าตาเป็นยังไง" เท่านั้น

---

## 1. สรุปสถานะโปรเจกต์

Session A-F.2 เสร็จสมบูรณ์ครบ commit+push แล้วทั้งหมด (ดู `PROJECT_STATE.md`
§6) เหลือ F.3-F.6:

- **F.3 (ต่อไปนี้)**: `doGet()`+HTML cascade UI
- F.4: เชื่อมปุ่ม "คำนวณ" กับ pipeline เต็ม
- F.5: Deploy web app จริง
- F.6: ทดสอบ end-to-end

---

## 2. F.3 คืออะไร — ยืนยันแล้ว vs. ยังต้องคุย

### 2.1 ยืนยันแล้ว (จาก `PROJECT_STATE.md` §6)

1. Cascade เต็มรูปแบบ: Drive folder → Google Sheets file → Sheet tab —
   เดินหาสดทุกครั้งผ่าน `listCategoryFolders()`/`listFilesInFolder(folderId)`/
   `listAlignmentTabsInFile(fileId)` ใน `GS_DriveWalker.gs` (Session F.2
   เสร็จแล้ว มี test function คู่กันครบใน `TestDrive.js`)
2. ปุ่ม "คำนวณ" ต้องรัน pipeline เต็มจริงทุกครั้ง — แต่การเชื่อมปุ่มเป็นงาน
   ของ F.4 ไม่ใช่ F.3
3. ผลลัพธ์เขียนกลับเข้าไฟล์เดียวกับข้อมูลต้นทาง เป็น 4 tab
   `result_(alignment)_Elements/CrossCheck_Points/CrossCheck_Radius/
   CrossCheck_Deflection` (parameterize แล้วใน F.1)

### 2.2 ยังไม่ตัดสินใจ — ต้องคุยกับ CK1024 ก่อนร่างโค้ด

- หน้าตา UI จริงๆ: cascade dropdown 3 ชั้นแบบไหน, placeholder/loading state
  ระหว่างรอ `google.script.run` ตอบกลับแต่ละชั้น
- **UX สำหรับหมวดที่ไม่มีไฟล์** (ตอนนี้ 7 ใน 8 หมวดว่างเปล่า) — ต้องแสดง
  ยังไงไม่ให้ดูเหมือนหน้าจอค้าง (เคย flag ไว้ตอนคุยสเปค F.2 แต่ยังไม่ได้
  ตัดสินใจจริง)
- โครงสร้าง `doGet()`: `HtmlService.createHtmlOutputFromFile()` ไฟล์เดียว
  หรือ `createTemplateFromFile()` แบบ template ผสม CSS/JS แยกไฟล์
- ขอบเขต F.3 เคร่งครัดแค่ไหน — เดิมวางแผนแยก F.3 (UI cascade อย่างเดียว)
  กับ F.4 (เชื่อมปุ่มคำนวณ) เป็นคนละสเต็ป ยังจะทำตามนี้ไหม

**งานแรกของแชทใหม่**: คุย 4 ข้อข้างต้นให้ได้ข้อสรุปก่อน แล้วค่อยร่าง draft
ตาม pattern Plan-Review-Approve เดิม

---

## 3. กฎเหล็กของโปรเจกต์ (ย่อ — เผื่อบริบทไม่ครบ)

- **Plan-Review-Approve เสมอ**: Claude Code เขียนแผน/draft → Claude Chat
  ตรวจก่อน → อนุมัติถึงเขียนไฟล์จริง
- **ห้าม save/commit โดยไม่แสดง diff ให้ตรวจก่อนเสมอ** — ไฟล์ `.gs`/`.js`
  ต้องอัปโหลดเป็นไฟล์จริงให้ Claude Chat อ่าน (ไม่ paste ผ่านข้อความ —
  เจอปัญหาเนื้อหาขาดหาย/เพี้ยนซ้ำหลายรอบตอน relay ผ่าน terminal ตลอด
  Session F.1-F.2)
- **Commit message ผ่าน `.git/smt_commit_msg.txt` ด้วย heredoc เท่านั้น** —
  **ใช้ forward slash เสมอ ไม่ใช่ backslash** (ดูหัวข้อ 4) ถ้า Write tool
  ถามจะ overwrite ไฟล์นี้ตรงๆ ให้กด **3 (No)** เสมอ เช็ค `cat -A` ก่อน
  commit ทุกครั้ง
- **คำสั่ง read-only** (`ls`, `cat`, `grep`, `find`, `diff`, `node --check`,
  `git log`, `git status`, `git diff`) — CK1024 อนุมัติเองได้เลยในเทอร์มินัล
  ไม่ต้องรอถาม Claude Chat — **คำสั่งเขียน/commit/push ยังต้องส่งมาให้
  Claude Chat ตรวจทุกครั้งเหมือนเดิม**
- **`clasp run-function`/`clasp logs` ใช้ไม่ได้** — รันทดสอบผ่าน Apps
  Script web editor จริงเสมอ (▶ Run → Execution log) CK1024 กดเอง
- **ไฟล์เดียวกันมีอยู่ 2 ที่เสมอ**: repo (`reference/gsheet/*.gs`,
  `TestDrive.js` ไม่ track) กับ clasp deploy folder (`D:\MyClasp_SMT_DEMO\*.js`
  แบบ flat) — `clasp push` อ่านจาก clasp folder เท่านั้น ต้อง copy ไฟล์ repo
  ไปที่นั่นก่อน push เสมอถ้าเป็นไฟล์ใหม่ — **ระบุ path เต็มชัดเจนทุกครั้ง
  กันอัปโหลดผิดไฟล์** (เจอปัญหานี้จริงตอน F.2)

---

## 4. บทเรียนสำคัญจาก Session F.1-F.2

- Diff/เนื้อหาไฟล์ที่ Claude Code relay ผ่าน terminal เพี้ยน/ขาดหายซ้ำ
  หลายรอบ (ตัดกลางคำ, บรรทัดติดกันผิด) — วิธีแก้เสมอ: อัปโหลดไฟล์จริงเข้า
  แชทตรงๆ ไม่ paste ผ่านข้อความ
- Heredoc เขียน commit message ต้องใช้ forward slash
  (`.git/smt_commit_msg.txt`) ไม่ใช่ backslash เวลารันผ่าน Claude Code bash
  tool (backslash ถูกตีความเป็น escape character ทำให้สร้างไฟล์ผิดชื่อแทน)
- ปรัชญาการออกแบบสำคัญ: ผู้ใช้เพิ่ม folder/file/tab ได้อิสระตลอดเวลา
  ระบบต้องเดินหาสดเสมอ ไม่ hardcode รายชื่อ และไม่ต้องสร้าง filter
  อัจฉริยะเกินจำเป็นเพื่อเดาว่า "อันไหนคือของจริง" — ให้ผู้ใช้เลือกเอง
  ปล่อยให้ pipeline validation (`issues` array) เป็น safety net แทน
- เมื่อไฟล์เดียวกัน (เช่น `.gs`/bundle เอกสาร) มีทั้งในเครื่อง CK1024 และใน
  sandbox ของ Claude Chat — ถ้า Claude Chat มีสำเนาที่ verify แล้วอยู่แล้ว
  (byte-exact) การสร้างไฟล์ขึ้นมาเองแล้วให้ดาวน์โหลดตรงๆ ปลอดภัยกว่าให้
  Claude Code ประกอบขึ้นใหม่หรือ relay เนื้อหายาวๆ ผ่าน terminal

---

## 5. ข้อความเริ่มแชทใหม่

```
นี่คือ handoff สำหรับเริ่ม Session F.3 (แนบไฟล์ HANDOFF_START_F3_20260728.md
พร้อม PROJECT_STATE.md, DEPENDENCY_MAP.md, BUNDLE_gsheet.md,
BUNDLE_python_core.md) — F.1-F.2 เสร็จสมบูรณ์แล้ว (push ขึ้น origin/main ที่
9e5e608)

F.3 ยังไม่มีสเปคละเอียด — ขอเริ่มจากคุยออกแบบ cascade UI ก่อนตามหัวข้อ 2.2
ในไฟล์ handoff
```
