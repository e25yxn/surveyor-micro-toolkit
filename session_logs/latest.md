# Session Log

## [2026-07-28 08:04] ปิด Session F.2 + เตรียม handoff Session F.3 — commit+push แล้ว

- ทำ: CK1024 วาง `BUNDLE_gsheet.md` (regenerate ใหม่ 9 ไฟล์ เพิ่ม
  `GS_DriveWalker.gs` ต่อท้ายตาม dependency order เดิม) และไฟล์ใหม่
  `HANDOFF_START_F3_20260728.md` (5 หัวข้อ: บริบท, สรุปสถานะ, F.3
  ยืนยันแล้ว vs ยังต้องคุย, กฎเหล็ก, บทเรียน F.1-F.2, ข้อความเริ่มแชทใหม่)
  ไว้ที่ repo root เองแล้ว (เนื้อหาผ่าน Claude Chat อนุมัติมาก่อนหน้านี้) —
  งานรอบนี้ของ Claude Code คือตรวจ + commit + push เท่านั้น ไม่มีการแก้
  เนื้อหาไฟล์ทั้งสอง
  - ตรวจ `git status` ก่อน: เห็นแค่ 2 ไฟล์ที่คาดไว้ (BUNDLE_gsheet.md
    modified, HANDOFF_START_F3_20260728.md untracked) ไฟล์ untracked อื่นๆ
    เป็นของเดิมที่ไม่เกี่ยวข้อง
  - ตรวจ diff BUNDLE_gsheet.md: +67/-0 บรรทัด เพิ่ม header note
    "Regenerated 2026-07-28..." กับ section ใหม่
    "## FILE: reference/gsheet/GS_DriveWalker.gs" ต่อท้ายไฟล์เดิมทั้งหมด
    (grep นับ "## FILE:" ได้ 9 จุดตรงตามคาด)
  - อ่าน HANDOFF_START_F3_20260728.md เต็มไฟล์ยืนยันครบ 5 หัวข้อตามสเปค
    อ้างอิง commit hash `9e5e608` (HEAD ก่อนหน้า) ตรงกับ git log จริง
  - `git add` เฉพาะ 2 ไฟล์นี้, ตรวจ `git status` ซ้ำว่า stage แค่ 2 ไฟล์
  - เขียน commit message ผ่าน bash heredoc ตรงตามคำสั่งชัดเจนของผู้ใช้
    (forward slash `.git/smt_commit_msg.txt` ตามบทเรียน F.2) — ทับ Write
    tool prompt ที่ถูกปฏิเสธ (`3. No`) ไปก่อนหน้า ตรวจ `cat -A` ยืนยันว่า
    เป็นข้อความใหม่ ไม่ใช่ข้อความเก่าของ commit F.2 close-out ที่ค้างอยู่
- คำสั่ง: `git status`, `git diff -- BUNDLE_gsheet.md`, `git diff --stat`,
  `grep -c "^## FILE:" BUNDLE_gsheet.md`, `git add BUNDLE_gsheet.md
  HANDOFF_START_F3_20260728.md`, heredoc เขียน `.git/smt_commit_msg.txt`,
  `cat -A .git/smt_commit_msg.txt`, `git commit -F .git/smt_commit_msg.txt`,
  `git log -1 --stat`, `git push`
- ผล: PASS — commit `367997e` (2 files changed, 197 insertions(+), 0
  deletions) push สำเร็จ `9e5e608..367997e main -> main`
- commit: `367997e`
- หมายเหตุ: ปิด Session F.2 สมบูรณ์แล้วทั้งโค้ดและเอกสาร handoff พร้อมเริ่ม
  Session F.3 ในแชทใหม่ (อัปโหลด 5 ไฟล์ตามที่ระบุใน handoff §0)

## [2026-07-28] Drive-walking backend functions for cascade UI — Session F.2, verified live incl. two rounds of real-world edge cases

- ทำ: สร้าง `reference/gsheet/GS_DriveWalker.gs` ใหม่ (ไฟล์ track จริง ไม่ใช่
  scratch — เป็น backend logic จริงที่ `doGet()` จะเรียกใช้ใน F.3+) มี 3
  ฟังก์ชัน: `listCategoryFolders()` (เดินจาก root `SMT_Web_App_demo`, hardcode
  เฉพาะ root ID เดียว), `listFilesInFolder(folderId)` (filter
  `MimeType.GOOGLE_SHEETS` กัน PDF/รูปที่ปนอยู่ในโฟลเดอร์),
  `listAlignmentTabsInFile(fileId)` (filter 2 ชั้น: ชื่อ tab ขึ้นต้น
  `result_` + header signature ตรงกับ 4 ตารางผลลัพธ์ที่รู้จัก — อ้างอิง
  `GS_ElementTable.HEADER`/`GS_CrossCheck.*_HEADER` ตรงๆ ไม่ copy ค่า กัน
  drift) ทั้ง 3 ฟังก์ชันเรียงผลลัพธ์ตามตัวอักษร (`localeCompare`) ก่อน
  return เพิ่มฟังก์ชันทดสอบคู่กัน 3 ตัวใน `TestDrive.js`
  (`testListCategoryFolders`/`testListFilesInFolder`/
  `testListAlignmentTabsInFile`) อัปเดต `DEPENDENCY_MAP.md` เพิ่มแถว
  `GS_DriveWalker` (พึ่ง `GS_ElementTable` + `GS_CrossCheck` โดยตรง)
- คำสั่ง: สร้างไฟล์ตาม draft ที่อนุมัติ, `clasp push`, รันทดสอบทั้ง 3
  ฟังก์ชันผ่าน Apps Script web editor 2 รอบ (ก่อน/หลังเพิ่ม sort)
- ผล: PASS ทั้งสองรอบ — รอบแรกเจอ edge case จริง 2 จุด: (1) เจอ 8 หมวดจริง
  (ไม่ใช่ 6-7 ตามที่บันทึกเก่าประมาณไว้ รวมหมวดที่ไม่เคยบันทึกมาก่อนคือ
  `007_Cross_Beam`) ยืนยันว่าตัดสินใจเดินหา Drive สดแทน hardcode ถูกต้อง
  เพราะ hardcode จะมองไม่เห็นหมวดใหม่นี้เลย (2) เจอ tab แปลกปลอม
  `Test_Sheet` ปนกับ `HOR-ORR-04` ในไฟล์เดียวกัน — ตรวจแล้วว่า filter
  ทำงานถูกตามสเปคทุกจุด ไม่ใช่บั๊ก CK1024 ยืนยันว่าทั้งสองจุดเป็นข้อมูล
  ทดสอบที่เพิ่มเองโดยตั้งใจ และชี้แจงว่าการใช้งานจริงตั้งใจให้ผู้ใช้เพิ่ม
  folder/file/tab ได้อิสระ ตัดสินใจ: ไม่ต้องสร้าง whitelist ตรวจ header
  เพิ่ม (เกินจำเป็น — ผู้ใช้เลือกเองอยู่แล้วเหมือน file browser, safety net
  จริงอยู่ที่ pipeline validation ใน F.4) — เพิ่ม sort ตามชื่อแทนเพื่อ UX ที่
  คาดเดาได้เมื่อรายการยาวขึ้นตามการใช้งานจริง รอบสองยืนยัน: 8 หมวดเรียงถูก
  (001→002→...→999), ไฟล์/tab เรียงถูกเช่นกัน (`HOR-ORR-04` ก่อน
  `Test_Sheet`)
- commit: feat (`reference/gsheet/GS_DriveWalker.gs`) + docs
  (`DEPENDENCY_MAP.md`, `PROJECT_STATE.md`, `session_logs/latest.md`) —
  ฟังก์ชันทดสอบ 3 ตัวใน `TestDrive.js` ไม่ track ใน git เหมือน F.1

## [2026-07-28 07:16] แก้ + push GS_DriveWalker.gs เพิ่ม result.sort() 3 จุด (Session F.2 follow-up) — รอผล log ก่อน commit

- ทำ: เพิ่ม `result.sort(function(a, b) {...localeCompare...})` ก่อน
  `return result;` ในทั้ง 3 ฟังก์ชันของ `reference/gsheet/GS_DriveWalker.gs`
  (`listCategoryFolders`, `listFilesInFolder` — sort ตาม `.name`;
  `listAlignmentTabsInFile` — sort ตาม string ตรงๆ เพราะ result เป็น
  array-of-string) ตาม draft ที่ Claude (แชท) อนุมัติ ไม่แตะส่วนอื่นของไฟล์
  แก้ `PROJECT_STATE.md` คู่กัน 6 จุด (ตาราง GAS files, จำนวนไฟล์ push,
  รายการ TestDrive.js, ตาราง session F, roadmap F.2, ดีไซน์ cascade) —
  ตรวจแล้วว่า `GS_DriveWalker.gs` ที่อัปโหลดไปให้ Claude (แชท) ตรวจรอบแรก
  พลาดหยิบไฟล์ผิด (หยิบ `D:\MyClasp_SMT_DEMO\GS_DriveWalker.js` เก่าแทน
  ไฟล์ repo จริง) แก้ความเข้าใจผิดแล้วอัปโหลดไฟล์ repo ตัวจริงไปตรวจซ้ำ ผ่าน
  แล้ว จึง copy ไฟล์ repo (มี sort ครบ) ทับ `D:\MyClasp_SMT_DEMO\
  GS_DriveWalker.js` เดิม (ยืนยัน byte-identical ด้วย `diff`) ก่อน push
- คำสั่ง: `cp reference/gsheet/GS_DriveWalker.gs D:/MyClasp_SMT_DEMO/GS_DriveWalker.js`,
  `diff` ยืนยัน byte-identical, `clasp push`
- ผล: PASS — clasp push สำเร็จ 12/12 ไฟล์เหมือนเดิม (เนื้อหา
  `GS_DriveWalker.js` อัปเดตเป็นเวอร์ชันมี sort แล้ว)
- commit: ยังไม่ commit — รอผู้ใช้ (CK1024) รัน 3 ฟังก์ชันทดสอบซ้ำผ่าน Apps
  Script web editor (`testListCategoryFolders` คาด 8 หมวดเรียง alphabetical,
  `testListFilesInFolder` คาด HOR-ORR-04 ไฟล์เดียวเหมือนเดิม,
  `testListAlignmentTabsInFile` คาด HOR-ORR-04 + Test_Sheet เรียง H ก่อน T)
  แล้วนำ Execution log กลับมาตรวจก่อน
- หมายเหตุ: บทเรียนรอบนี้ — เมื่อไฟล์เดียวกันมีอยู่ 2 ที่ (repo กับ clasp
  deploy folder) ต้อง sync ให้ตรงกันทุกครั้งก่อนอัปโหลดให้ Claude (แชท)
  ตรวจ และก่อน push จริง ระบุ path เต็มชัดเจนเสมอกันสับสนซ้ำ

## [2026-07-28 06:26] clasp push GS_DriveWalker.gs (Session F.2) — รอผล Execution log ก่อน commit

- ทำ: หลัง Claude (แชท) ตรวจ 3 ไฟล์ผ่านแล้ว (GS_DriveWalker.gs, TestDrive.js,
  DEPENDENCY_MAP.md ตรง draft ทุกจุด) อนุมัติให้ push:
  - copy `reference/gsheet/GS_DriveWalker.gs` (approved content, byte-identical
    ยืนยันด้วย `diff`) ไปเป็น `D:\MyClasp_SMT_DEMO\GS_DriveWalker.js` — ขั้นตอนนี้
    ไม่ได้เขียนไว้ชัดในแผนเดิม (แผนพูดแค่สร้างไฟล์ใน repo + แก้ TestDrive.js)
    แต่จำเป็นเพื่อให้ `clasp push` เห็นไฟล์ใหม่ (clasp push จากโฟลเดอร์
    `D:\MyClasp_SMT_DEMO\` เท่านั้น ไม่รู้จัก `reference/gsheet/`)
  - `clasp push` ครั้งแรก (ก่อน copy) ได้แค่ 11 ไฟล์ตามที่คาด (ไม่มี
    GS_DriveWalker.js) — ยืนยันว่าต้อง copy ก่อนจริง ไม่ใช่ clasp bug
  - `clasp push` ครั้งที่สอง (หลัง copy) ได้ 12 ไฟล์ตามที่ผู้ใช้คาดไว้
- คำสั่ง: `cp reference/gsheet/GS_DriveWalker.gs D:/MyClasp_SMT_DEMO/GS_DriveWalker.js`,
  `diff` ยืนยัน byte-identical, `clasp push` (x2)
- ผล: PASS — clasp push สำเร็จ 12/12 ไฟล์ (`appsscript.json`, `code.js`,
  `FPMath.js`, `GS_Alignment.js`, `GS_AlignmentBuilder.js`, `GS_CrossCheck.js`,
  `GS_DriveWalker.js`, `GS_ElementTable.js`, `GS_PiTableParser.js`,
  `GS_TableSplitter.js`, `TestDrive.js`, `WCB.js`)
- commit: ยังไม่ commit — รอผู้ใช้ (CK1024) รัน 3 ฟังก์ชันทดสอบผ่าน Apps Script
  web editor ด้วยตัวเอง (`testListCategoryFolders`, `testListFilesInFolder`,
  `testListAlignmentTabsInFile`) แล้วนำ Execution log กลับมาตรวจก่อน
- หมายเหตุ: `D:\MyClasp_SMT_DEMO\` ไม่ใช่ git repo (ยืนยันด้วย `git status` คืน
  "not a git repository") จึงไม่มี git diff ให้ดูฝั่งนั้นโดยตรง ใช้ diff เต็มไฟล์
  แบบ manual ในแชทแทนตอนตรวจ (ตามที่ Claude แชทตรวจผ่านแล้วรอบก่อนหน้า)

## [2026-07-27] parameterize export functions ใน TestDrive.js — Session F.1, verify diff เทียบ draft ที่อนุมัติ + รันจริงผ่าน Apps Script

- ทำ: parameterize `exportElementsToSheet()`/`exportCrossCheckToSheet()` ใน
  `D:\MyClasp_SMT_DEMO\TestDrive.js` ให้รับ `ss` + `alignmentName` เป็น
  parameter แทน hardcode `SPREADSHEET_ID` เดิม เปลี่ยนชื่อ tab ผลลัพธ์เป็น
  `result_(alignmentName)_Elements` / `result_(alignmentName)_CrossCheck_Points`
  / `result_(alignmentName)_CrossCheck_Radius` /
  `result_(alignmentName)_CrossCheck_Deflection` อัปเดต
  `testFullPipelineExportAgainstHorOrr04()` และ
  `testFullCrossCheckAgainstHorOrr04()` ให้เรียกฟังก์ชันแบบใหม่ (ส่ง
  `ss`+`SHEET_NAME` เป็น alignment name) — ไม่มีการแก้ logic คำนวณใดๆ ทั้งสิ้น
  เป็นแค่ signature/tab-naming change
  - สำรอง `TestDrive.js.bak_20260727` ไว้ในโฟลเดอร์เดียวกันก่อนแก้จริง
  - diff เต็มไฟล์ตรวจใน Claude Chat ตรงตาม draft ที่อนุมัติทุกจุด ไม่มีบรรทัด
    อื่นถูกแตะ
- คำสั่ง: `cp TestDrive.js TestDrive.js.bak_20260727`, Edit 4 จุดตาม draft,
  `diff -u` เทียบไฟล์สำรอง, `clasp push`, รัน
  `testFullPipelineExportAgainstHorOrr04()` และ
  `testFullCrossCheckAgainstHorOrr04()` ผ่าน Apps Script web editor
- ผล: PASS — `clasp push` สำเร็จ (11 ไฟล์) รันทดสอบจริงผ่าน Apps Script web
  editor: `testFullPipelineExportAgainstHorOrr04` (Elements tab 26×8, header
  ตรง) และ `testFullCrossCheckAgainstHorOrr04` (CrossCheck_Points 23×6,
  CrossCheck_Radius 11×10, CrossCheck_Deflection 10×5) — ผลตรงกับ Session D/E
  ทุกตัวเลข รวม PI-1/PI-11 special-case notes เดิม ไม่มี regression
- commit: (docs เท่านั้น — ดูหมายเหตุ)
- หมายเหตุ: `TestDrive.js` ไม่ track ใน git (ตกลงไว้ตั้งแต่ต้น เพราะเป็นไฟล์
  ทดสอบใน clasp folder แยกต่างหาก `D:\MyClasp_SMT_DEMO\`) — commit รอบนี้จึง
  เป็น docs ล้วน (`PROJECT_STATE.md` + `session_logs/latest.md`) ไม่มี feat
  commit ควบคู่

## [2026-07-26] export ตารางที่ 2 (cross-check 3 ตารางย่อย) — Session E, verify diff=0 กับ Python + live Sheet

- ทำ: เพิ่ม GS_CrossCheck.gs สร้าง 3 ตาราง cross-check ต่อจาก GS_ElementTable.gs
  (Session D):
  - ตาราง 2a (CrossCheck_Points): mirror `check.py::check_horizontal()` ตรงๆ
    verify diff=0 เทียบ Python จริงครบ 22 แถว x 5 คอลัมน์ (name/sta/deltaN/
    deltaE/gap/ok) ภายใน 1e-9
  - ตาราง 2b (CrossCheck_Radius) / 2c (CrossCheck_Deflection): logic ใหม่
    ไม่มี oracle ให้ mirror (ออกแบบไว้ใน session_logs/plan_20260726_1558.md
    ที่อนุมัติแล้ว) — แต่ละ PI โค้งธรรมดา คำนวณ tangent length/deflection
    ตามแบบจริงจากแถว PC/PT ข้างเคียงในตารางดิบ (จับคู่ตามลำดับแถวเดิม ไม่ใช่
    จาก vertexRows/drawing ที่แยกไปแล้ว) เทียบกับรัศมี/deflection ออกแบบ
    verify ด้วย Python prototype อิสระ + ตรวจมือหลายจุดก่อนพอร์ต
  - กฎ EP-substitution: PI-11 ไม่มีแถว PT แยกในตารางดิบ (โค้งสุดท้ายจบเกือบ
    พอดีที่ EP) — ใช้พิกัด EP แทนได้เฉพาะเมื่อ PT ที่ buildFromPI() คำนวณจริง
    อยู่ใกล้ EP ภายใน snap tolerance เท่านั้น (ยืนยันด้วย engine จริง ไม่ใช่เดา
    gap จริงที่วัดได้ = 0.19 มม.)
  - เพิ่ม assertion เช็ค vertices.length ตรงกับจำนวนแถว vertex ที่
    scanRawRows_ นับได้ กัน PI จับคู่ PC/PT ผิดตำแหน่งแบบเงียบๆ — ยืนยันแล้ว
    ว่า throw จริงด้วย negative test (บังคับข้อมูลผิด 12 vs 13 แถว)
  เพิ่ม exportCrossCheckToSheet() (เขียน 3 tab: CrossCheck_Points/Radius/
  Deflection) + testFullCrossCheckAgainstHorOrr04() ใน TestDrive.js
- คำสั่ง: Node diff เทียบ check_horizontal() จริง (diff=0), node
  reference/gsheet/smoke_test.js, pytest -q, clasp push, รัน
  testFullCrossCheckAgainstHorOrr04() ผ่าน Apps Script web editor + Execution
  log, git commit -F .git/smt_commit_msg.txt
- ผล: PASS — smoke_test.js 23/23, pytest 504 passed, live Sheet execution
  ตรงกับ Python prototype ทุกค่า (Table 2a spot-check + ตาราง 2b ครบ 10 PI +
  ตาราง 2c ครบ 9 PI)
- commit: d9d95e6
- หมายเหตุ — 3 บทเรียนสำคัญที่เจอระหว่างทาง (ทั้งหมดแก้/ตรวจสอบก่อนพอร์ตแล้ว):
  1. **สูตร deflection ตามแบบจริง**: แผนแม่ (HANDOFF_SMT_SESSION_E_PLAN) เขียน
     ว่า "มุมระหว่างเวกเตอร์ PI→PC กับ PI→PT" ซึ่งถ้าทำตามตัวอักษรจะได้
     `180°−Δ` ไม่ใช่ `Δ` จริง (เวกเตอร์ PI→PC ชี้ย้อนทางเดินทาง) แก้เป็น
     `azimuth(PC→PI)` กับ `azimuth(PI→PT)` แทน (ทิศทางเดินทางจริง) ก่อนพอร์ต
     ดู session_logs/plan_20260726_1558.md §2
  2. **PI-11/EP ที่เคยเข้าใจผิดว่าเป็นบั๊ก**: ระหว่างวางแผน เคยเขียนไว้ผิดว่า
     PT ของ PI-11 "เลย EP ไป ~4.8 ม." ซึ่งคำนวณผิดจากการเอา PI_sta ดิบบวก
     T_in ตรงๆ (ไม่ใช่วิธีคำนวณ station ที่ถูกต้อง) — ตรวจสอบซ้ำด้วยการรัน
     buildFromPI() จริงแล้วพบว่าโค้งจบห่างจาก EP แค่ 0.19 มม. เท่านั้น ไม่มี
     ปัญหาจริง ไม่กระทบ core geometry ที่ verify แล้วใน Session C ถอนคำพูด
     จุดนั้นในแผนที่อนุมัติแล้ว ดู session_logs/plan_20260726_1558.md §3.1
  3. **EP-substitution guard**: จากบทเรียนข้อ 2 เลยออกแบบให้ใช้พิกัด EP แทน
     แถว PT ที่ขาดหายได้ (เฉพาะ PI-11 ในชุดข้อมูลนี้) แต่ต้อง guard ด้วยการ
     เช็ค PT ที่ engine คำนวณจริงว่าอยู่ใกล้ EP ภายใน snap tolerance ก่อน
     เสมอ (ไม่ใช่ substitute แบบไม่มีเงื่อนไข) กันกรณีอื่นที่โค้งสุดท้ายไม่ได้
     จบใกล้ EP จริงจะถูก mis-apply กฎนี้ผิดที่

## [2026-07-25] export ตารางที่ 1 (element table) — Session D, verify diff=0 กับ Python ทุกจุด

- ทำ: เพิ่ม GS_ElementTable.gs ให้ flatten `elements` array จาก
  GS_AlignmentBuilder.buildFromPI() เป็นตาราง 8 คอลัมน์ (StaStart, StaEnd, N,
  E, Azimuth, Radius, Type, Transition) mirror src/smt/cli.py::_run_build
  (บรรทัด 118-168) และ _radius_from_element() (บรรทัด 109-115) รวมพฤติกรรม
  blank Transition เป็น '' สำหรับ element T/C เก็บค่าเป็นตัวเลขจริงแทน string
  ปัดทศนิยม (.6f) เพื่อให้ใช้สูตร sort/sum บน Sheet ได้ตรงๆ verify diff=0
  เทียบ Python ครบทั้ง 25 rows/8 คอลัมน์ รวมเช็คแถว SPIN/SPOUT ว่า Transition
  ถูกต้อง
  เพิ่ม exportElementsToSheet(elements) ใน TestDrive.js — เช็ค tab "Elements"
  ผ่าน ss.getSheetByName ก่อน ถ้ามีอยู่แล้วให้ clear() แล้วเขียนทับ (ไม่
  insertSheet ซ้ำ กัน error ชื่อซ้ำ) เขียน [HEADER, ...rows] ด้วย setValues()
  ครั้งเดียว
  เพิ่ม testFullPipelineExportAgainstHorOrr04() ทดสอบ pipeline เต็ม
  (split→parse→build→export) กับ Sheet HOR-ORR-04 จริง แล้วอ่านค่ากลับจาก tab
  "Elements" มาเช็ค
- คำสั่ง: clasp push, รัน testFullPipelineExportAgainstHorOrr04() ผ่าน Apps
  Script web editor + Execution log, git commit -F .git\smt_commit_msg.txt
- ผล: PASS — Elements tab ถูกสร้าง/เขียนถูกต้อง diff=0 ทุกจุดเทียบ Python
- commit: b3e5926
- หมายเหตุ: exportElementsToSheet() hardcode SPREADSHEET_ID ไว้ในตัวเอง แทนที่
  จะรับ ss เป็น parameter — ใช้ได้ปกติสำหรับไฟล์ทดสอบตอนนี้ แต่ต้องแก้ตอน
  Session F ที่ต้องรองรับหลาย alignment/หลายสเปรดชีต

## [2026-07-25] ต่อ pipeline เต็ม split→parse→build แล้ว verify end-to-end สำเร็จ — Session C

- ทำ: wiring test เต็ม pipeline (split→parse→build) ยืนยัน GS_AlignmentBuilder.gs
  (v2.0) เป็น oracle ที่ถูกต้อง, verify ผ่าน Node/Python (diff=0 ทั้งข้อมูลจริงและ
  PI-only) เจอว่า D:\MyClasp_SMT_DEMO ไม่เคยมี FPMath.js/WCB.js/GS_Alignment.js/
  GS_AlignmentBuilder.js เลย (Groups A/B/C ที่เคย verify ไว้ก่อนหน้าทำคนละโปรเจกต์
  sandbox) เพิ่ม 4 ไฟล์นี้เข้า clasp folder (คัดลอก verbatim จาก reference/FPMath.gs,
  reference/WCB.gs, reference/gsheet/GS_Alignment.gs,
  reference/gsheet/GS_AlignmentBuilder.gs) แล้ว push สำเร็จ พร้อมเพิ่มฟังก์ชัน
  testBuildFromPIAgainstHorOrr04() ต่อท้าย TestDrive.js
  รันจริง testBuildFromPIAgainstHorOrr04() บน Sheet HOR-ORR-04: elements=25,
  control=26, issues=0 ตรงตามคาด ตอนแรกดูเหมือนพิกัดจุด PC/PT ต่างจากที่ verify
  ไว้มาก แต่พิสูจน์แล้วว่าเป็นผลจากพิกัด BP ที่ต่างกัน 5 มม. (CSV fixture vs
  ชีตจริง) ขยายผลผ่านเรขาคณิตช่วงสั้นๆ ใกล้ BP เท่านั้น ไม่ใช่บั๊ก (ยืนยันด้วยการ
  ป้อน vertices จากชีตจริงเข้า Python โดยตรง ได้ผลตรงกับ log ทุกตัวเลข)
- คำสั่ง: clasp pull, clasp push, รัน testBuildFromPIAgainstHorOrr04() ผ่าน Apps
  Script web editor + Execution log
- ผล: PASS — pipeline ทำงานถูกต้องสมบูรณ์ end-to-end
- commit: ไม่มี (ไม่มีไฟล์ repo เปลี่ยนแปลง — 4 ไฟล์ dependency มีอยู่แล้วใน
  reference/ ไม่ได้แก้, TestDrive.js อยู่นอก repo)
- หมายเหตุ: —

## [2026-07-25] พอร์ต GS_PiTableParser.gs เสร็จ — Session B, verify diff=0 ทั้ง Node/Python และ Sheet จริง

- ทำ: พอร์ต parse_pi_table() (alignment_builder.py:219-328) เป็น
  GS_PiTableParser.gs — reuse parseHeader_/cell_ pattern จาก GS_TableSplitter.gs,
  mirror pending/flush state machine, R+compound ambiguity error, R blank/"0"
  = angle point, LsIn/LsOut override Ls, เพิ่ม toFloat_() helper mirror
  พฤติกรรม float() ของ Python (throw แทน parseFloat ที่ปล่อยผ่านเงียบๆ)
  ยืนยัน contract กับ buildFromPI ที่มีอยู่แล้ว: ตรงกัน 8/9 key (n,e,sta,R,Ls,
  LsIn,LsOut,trans,compound) ส่วน transIn/transOut ไม่กระทบ (parse_pi_table
  ไม่เคยผลิต key นี้อยู่แล้ว และ buildFromPI fallback ไปที่ .trans เอง)
  Verify 2 ชั้น: (1) Node.js เทียบ Python จริง 8 เคส (ข้อมูลจริงผ่าน pipeline
  เต็ม + 7 synthetic case ครอบคลุม symmetric Ls, angle point, compound
  sub-row, ambiguous error, BP sta, LsIn-only) diff=0 ทุกจุด (2) รันจริงผ่าน
  Apps Script กับ Sheet HOR-ORR-04 จริง (vertexRows=14, vertices=13) ตรงกับ
  Node/Python ทุกฟิลด์ (ต่างแค่ทศนิยมส่วนเกินตามที่รู้จักแล้ว) ไม่มี regression
  ที่ PI-10
- คำสั่ง: Node.js verify script, clasp push, รัน testParseAgainstHorOrr04 ผ่าน
  Apps Script web editor, git commit -F .git\smt_commit_msg.txt
- ผล: PASS — diff=0 ทั้งสองชั้นการ verify
- commit: a4a094b
- หมายเหตุ: บันทึก backlog เรื่อง transIn/transOut ไม่รองรับผ่าน CSV
  (pre-existing limitation ทั้งสองฝั่ง ไม่ใช่ปัญหาจาก Session B)

## [2026-07-25] แผน element export — Session A สำรวจ (อ่านอย่างเดียว ไม่แก้โค้ด)

- ทำ:
  - อ่าน `src/smt/builders/alignment_builder.py` เต็มไฟล์ — ยืนยัน signature จริง:
    - `parse_pi_table(rows) -> list[dict]`, `build_alignment_from_pi(vertices) -> BuildResult`
      (`NamedTuple(elements, control, issues)`)
    - `Element` (dataclass, `alignment.py:83-99`) มี field: `type, sta_start, sta_end,
      n, e, azimuth, k_in, k_out, transition` — ไม่มี radius ตรง ๆ (ต้องคำนวณจาก
      `1/k_in` หรือ `1/k_out`) และไม่มี deflection angle เก็บไว้เลย
    - `ControlPoint` (dataclass) มีแค่ 4 field: `name, sta, n, e`
    - `check_against_drawing(control, drawing, tolerance)` คืน dict ต่อจุด
      `{name, sta_calc, sta_draw, gap_m, ok}` — คำนวณแค่ `gap_m` รวม (hypot ของ N,E)
      เท่านั้น ไม่มี delta แยกแกน ไม่มี radius/deflection
  - grep "element"/"export"/"flatten" ทั่ว `src/smt/` — พบว่า logic flatten ตารางที่ 1
    มีอยู่แล้วใน `cli.py::_run_build` (`smt build`, บรรทัด 118-168) และถูก mirror ใน
    `app.py` (Streamlit UI) — header ตรงกัน: `StaStart, StaEnd, N, E, Azimuth, Radius,
    Type, Transition` (Radius แปลงจาก k_in/k_out ผ่าน `_radius_from_element()`)
  - หาที่มา `elements_for_excel.csv` (ไฟล์ untracked) — grep ทั่ว repo ไม่เจอชื่อไฟล์นี้
    ในโค้ดเลย เทียบเนื้อหาแล้วตรงกับ `elements_output.csv` ทุกคอลัมน์ เพียงตัด header
    ออก → สรุปว่าเป็นไฟล์ copy มือ (ตัด header) เพื่อ paste ใส่ Excel Named Range
    `SMT_Elements` ไม่ใช่ output อัตโนมัติจากฟังก์ชันไหน
  - เช็ค 3 ฟังก์ชันเทียบกันสำหรับตารางที่ 2 (cross-check comparison):
    - `check_against_drawing()` — gap_m รวมเท่านั้น, ไม่มี production caller
    - `check_horizontal()` (`check.py:113-147`) — คืน `HorizontalCheckResult`
      (`delta_n, delta_e, gap_metres, is_ok`) แยกแกนแล้ว แต่ grep ทั่ว repo (รวม
      cli.py, app.py) ไม่พบ production caller เลย — มีแค่ `tests/test_check.py`
      คลุมอยู่ (dead-but-tested)
    - `bulk_cross_check()` (`check.py:150-178`) — คืน `list[FieldCrossCheckResult]`
      (`name, n, e, z, sta, offset, disc`) เป็น inverse (N,E → sta,offset) สำหรับจุด
      สำรวจสนามลอย ๆ ไม่มี delta/radius/deflection เลย และเป็นคนละงานกับ Table 2
      — มี production caller จริงคือ `cli.py::_run_cross_check` (`smt cross-check`)
    - ไม่มีฟังก์ชันไหนใน 3 ตัวนี้คำนวณ radius delta หรือ deflection delta
  - ยืนยัน `smt build` (`_run_build`) กับ `smt cross-check` (`_run_cross_check`) เป็น
    2 subcommand แยกกันเลย (`cli.py:350-368`) — `_run_build` ไม่เรียก
    `bulk_cross_check()` ต่อท้ายแต่อย่างใด ผู้ใช้ต้องรัน `smt cross-check` แยกเอง
- คำสั่ง: Read + Grep เท่านั้น (ไม่มีคำสั่งแก้ไฟล์ ไม่มี pytest — สำรวจอย่างเดียวตาม
  scope ของ Session A ใน `session_logs/PLAN_SMT_ELEMENT_EXPORT_20260724.md`)
- ผล: N/A (ไม่มีการรันทดสอบ — งานนี้คือสำรวจ/อ่านโค้ดอย่างเดียว)
- commit: ไม่มี (ไม่มีการแก้ไฟล์ในงานนี้)
- หมายเหตุ:
  - สรุปผล Session A: **ตารางที่ 1** พอร์ตจาก `cli.py::_run_build` ตรง ๆ ได้เลย
    (คอลัมน์ชัดเจนแล้ว, Session D จะเบา) / **ตารางที่ 2** ต้องต่อยอดจาก
    `check_horizontal()` (มี delta_n/delta_e ให้แล้ว ตรงโจทย์ที่สุดในบรรดา 3 ตัว)
    แต่ Session E ต้องเขียนส่วน radius delta + deflection delta เพิ่มเองทั้งหมด
    เพราะไม่มีที่ไหนในโค้ดคำนวณไว้เลยแม้แต่ที่เดียว
  - รอ Claude (แชท) วางแผน Session B (พอร์ต `parse_pi_table()` เป็น GAS) ต่อ —
    ยังไม่เริ่มเขียนโค้ดใด ๆ

## [2026-07-24] พอร์ต GS_TableSplitter.gs เสร็จ — verify diff=0 กับ Sheet HOR-ORR-04 จริง, พบ+แก้ข้อมูล PI-10 ผิด

- ทำ:
  - พอร์ต `src/smt/builders/table_splitter.py::split_mixed_alignment_table()` เป็น
    Google Apps Script — สร้าง `reference/gsheet/GS_TableSplitter.gs`
    (`GS_TableSplitter.splitMixedAlignmentTable(rows)`) รับตาราง array-of-arrays
    (แถวแรก=header) แยกเป็น `vertexRows` (BP/PI-n/EP + compound sub-row) กับ
    `drawing` ({name,sta,n,e}) ตัด thousands-separator comma ออกจากตัวเลขเหมือน
    Python ต้นฉบับทุกประการ — adapter เท่านั้น ไม่แตะ parse/build/check เดิม
  - เขียน `testSplitAgainstHorOrr04()` ใน `D:\MyClasp_SMT_DEMO\TestDrive.js`
    (นอก git repo — โฟลเดอร์ clasp แยกต่างหาก) อ่านจริงจาก Google Sheet
    `HOR-ORR-04` (`SPREADSHEET_ID` เดิมที่เคยเข้าใจผิดว่าเป็น SMT_COGO_Builder_DEMO
    ยืนยันแล้วว่าเป็นไฟล์ HOR-ORR-04 จริง) เรียก `splitMixedAlignmentTable()`
    แล้ว log โครงสร้างผลลัพธ์ทั้งหมด
  - `clasp push` ยืนยันว่า `GS_TableSplitter.js` ถูกส่งขึ้น Apps Script project จริง
    ก่อนรัน (4 files: appsscript.json, code.js, GS_TableSplitter.js, TestDrive.js)
  - ระหว่าง verify พบว่าการเทียบผลลัพธ์ split (diff) ที่ PI-10 ไม่ตรงกัน เพราะข้อมูล
    ในสเปรดชีต HOR-ORR-04 เอง (ไม่ใช่บั๊กโค้ด): EASTING ผิดไปประมาณ 1000 เมตร และ
    ช่อง Transition ว่างเปล่า (ควรเป็น CLOTHOID) — ผู้ใช้ (CK1024) แก้ตรงในสเปรดชีต
    เป็น EASTING=681827.952 + Transition=CLOTHOID
  - รัน `testSplitAgainstHorOrr04()` ซ้ำหลังแก้ข้อมูล — ผลตรงกับ Python 100% ทุกฟิลด์
- คำสั่ง: `clasp push`, รัน `testSplitAgainstHorOrr04` ผ่าน Apps Script web editor
  (Execution log), `git commit -F .git\smt_commit_msg.txt`
- ผล: PASS — Sheet HOR-ORR-04 จริง 36 แถว → 14 vertexRows + 22 drawing entries
  ตรงกับ Python reference (`split_mixed_alignment_table()`) ทุกฟิลด์ diff=0
- commit: `67d06e4`
- หมายเหตุ: ปัญหา PI-10 (EASTING/Transition) เป็นความผิดพลาดของข้อมูลในสเปรดชีต
  HOR-ORR-04 เอง ไม่ใช่บั๊กของ `GS_TableSplitter.gs` หรือ Python ต้นฉบับ — ค้นพบ
  เพราะการ verify รอบนี้เท่านั้น

## [2026-07-23] เพิ่ม split_mixed_alignment_table() — table splitter สำหรับตารางที่มี BP/PI-n/PT/PC/TS/SC/CS/ST/EP ปนกัน

- ทำ:
  - สร้าง `src/smt/builders/table_splitter.py` — ฟังก์ชันใหม่ `split_mixed_alignment_table()`
    รับตารางดิบที่มี BP/PI-n/PT/PC/TS/SC/CS/ST/EP ปนแถวเดียวกัน แล้วแยกเป็น vertex_rows
    (POINT ตรง regex `^(BP|PI-\d+|EP)$` หรือ blank compound sub-row) ป้อนต่อ `parse_pi_table()`
    ได้ตรง ๆ กับ drawing list (จุดที่เหลือ) ป้อนต่อ `check_against_drawing()` ได้ตรง ๆ
    รวมถึงตัด thousands-separator comma ออกจากตัวเลข (เช่น `"1,537,772.85"`) ที่
    `parse_pi_table()`/`float()` เดิมไม่รองรับ
  - **ไม่แก้** `parse_pi_table()`, `build_alignment_from_pi()`, `check_against_drawing()` เลย
    (auto-derive R sign ที่มีอยู่แล้วในโค้ดทั้ง Python core และ GAS mirror ไม่ต้องเขียนใหม่ —
    งานนี้คือ table-splitter adapter ใหม่เท่านั้น)
  - สร้าง `tests/builders/test_table_splitter.py` — golden fixture จาก
    `test_data/HOR_ORR_04.csv` จริง (11 PI, ไม่มี compound) ยืนยัน split ถูกต้อง (13 vertex
    rows, 22 drawing points) และ cross-check ผ่านครบ 22/22 จุดจริง ที่ tolerance=0.1
    (gap_m สูงสุด 0.0789 เมตร)
- คำสั่ง: `.venv\Scripts\python.exe -m pytest -q`,
  `.venv\Scripts\python.exe -m pytest tests/builders/test_table_splitter.py -v`
- ผล: PASS — 504/504 ทั้ง suite, 11/11 test ใหม่ (ไม่มี skip)
- commit: `7abd919`
- หมายเหตุ: อ้างอิงแผนที่อนุมัติแล้วที่ `session_logs/plan_20260723_1804.md`

## [2026-07-23] แก้ transcription error พิกัด PI-10 ใน test_data/HOR_ORR_04.csv

- ทำ: ระหว่างเตรียม golden fixture ให้ `split_mixed_alignment_table()` พบว่า cross-check
  พังหนัก (gap 100–420 เมตร) ตั้งแต่โค้ง PI-9 เป็นต้นไป สืบสาเหตุพบว่าพิกัด PI-10 ในไฟล์
  (`NORTHING=1,537,748.127`, `EASTING=682,827.952`) คลาดเคลื่อนจากจุดตัดเส้นสัมผัส
  (tangent-intersection) ที่คำนวณจาก TS/SC/CS/ST รอบๆ ประมาณ 1000 ทั้งสองแกน (ΔN=1000.23,
  ΔE=1000.43) ผู้ใช้ (CK1024) เช็คกับ source survey ต้นทางจริงแล้วยืนยันค่าที่ถูกต้องคือ
  N=1,536,748.127, E=681,827.952 (ตรงกับที่คำนวณได้พอดี 1000.000 ทั้งสองแกน) แก้เฉพาะ 2
  ค่านี้ในไฟล์ ไม่แตะค่าอื่น — รายละเอียดครบใน
  `session_logs/investigate_hor_orr04_pi10_typo.md`
- คำสั่ง: คำนวณ tangent-intersection ยืนยัน (scratchpad script, ไม่ได้ commit), ผู้ใช้ยืนยัน
  ด้วยวาจาเทียบ source ต้นทาง
- ผล: PASS — หลังแก้ cross-check ผ่านครบ 22/22 จุด (ดู entry ด้านบน สำหรับ pytest run เต็ม)
- commit: `2074343`
- หมายเหตุ: ไม่ใช่บั๊กของ `alignment_builder.py` — ปัญหาอยู่ที่ข้อมูล survey ต้นทางเท่านั้น

## [2026-07-13] cosmetic cleanup — แก้ชื่อค้าง "AlignmentBuilderV2" ใน JSDoc header ของ GS_AlignmentBuilder.gs

- ทำ: แก้บรรทัด 5 ของ `reference/gsheet/GS_AlignmentBuilder.gs` (JSDoc header บนสุด) จาก
  "AlignmentBuilderV2" เป็น "GS_AlignmentBuilder" ให้ตรงกับชื่อไฟล์/module จริงหลัง `git mv`
  (ค้างไว้เป็นรายการ cleanup ตั้งแต่ commit `a4f7ae1` — ดู entry ด้านล่าง) ยืนยันก่อนแก้ว่า
  git status สะอาด (เหลือแค่ 4 ไฟล์ untracked เดิมที่ไม่เกี่ยวข้อง) และ HEAD คือ `a4f7ae1` จริง
- คำสั่ง: `git status`, `git log -1 --oneline`, `git diff -- reference/gsheet/GS_AlignmentBuilder.gs`
- ผล: PASS — diff มีแค่บรรทัดเดียวตามที่ตั้งใจ ไม่กระทบโค้ด (เป็น comment ล้วนๆ)
- commit: `1ed6b8e`
- หมายเหตุ: commit แยกต่างหาก ไม่รวมกับงาน GAS port หลัก ตามคำสั่งผู้ใช้

## [2026-07-13] พอร์ต GAS §5 เสร็จสมบูรณ์ — ทดสอบ Google Sheets จริง Group A/B + Node Group C, ปิดเอกสาร pre-commit gate

- ทำ:
  - ทดสอบ Google Sheets จริง (§5 ของแผน) **Group A**: พิมพ์สูตร `=GS_COSINE_TANGENT_LENGTH` /
    `=GS_COSINE_THETA_DEG` / `=GS_COSINE_TOTAL_Y` ในเซลล์จริง 3 จุด (R=900/L=100, R=250/L=50,
    R=500/L=70) = 9 ค่า ตรงกับค่าคาดไว้ในแผนทุกตัว ทั้งก่อนและหลังแก้ปัญหา FPMath/WCB
    dependency setup ใน Sheets project
  - **Group B**: COSINE ผ่าน `buildFromPI` (BP=(0,0), IP=(1000,0), R=900/Ls=100/trans=COSINE,
    EP ที่ deflection 30°) พิมพ์ในเซลล์ Sheets จริง ตรงกับ Python
  - **Group C**: CLOTHOID ผ่าน `buildFromPI` (vertex เดียวกับ Group B เปลี่ยนแค่ `trans`) —
    ยืนยัน python3 ตรงๆ ก่อน (deflection=30.000000000000018°, มุมเลี้ยว spiral
    =3.1830988618378955° ตรงสูตรเชิงเส้น `Ls/(2R)` เป๊ะ) แล้วรัน Node เปรียบเทียบ
    `GS_AlignmentBuilder.buildFromPI` กับ Python ผ่าน scratchpad script
    `compare_groupC_clothoid.js` — ตรงกันทุกบิตทั้ง 6 control point (BP/TS/SC/CS/ST/EP)
    และทุก element field — **ไม่ได้พิมพ์ในเซลล์ Google Sheets จริง** ต่างจาก Group A/B
  - ปิดเงื่อนไขก่อน commit ที่เหลือฝั่งเอกสาร (4 จุด แสดง diff ให้ผู้ใช้ตรวจก่อน save ทุกจุด):
    1. `reference/gsheet/GS_Alignment.gs` — เพิ่ม comment "Expected values" ท้ายไฟล์ ระบุ 9 ค่า
       ที่ verify จริงจาก Sheets (Group A)
    2. `reference/gsheet/GS_AlignmentBuilder.gs` — แก้ header comment (เดิมบรรทัด 28-29) ที่
       เขียนว่า "curveSubs_ patch ยังไม่เสร็จ — รอ session ถัดไป" (ล้าสมัยแล้ว) เป็นสรุปสถานะจริง:
       patch เสร็จสมบูรณ์ + ผลตรวจครบทุกชั้น ระบุแยกชัดว่า Group A/B ผ่าน Sheets จริง ส่วน
       Group C ผ่านแค่ Node
    3. `docs/extensions.md` EXT-003 — เพิ่มหัวข้อย่อย "GAS (Google Apps Script) mirror" อ้างอิง
       ไฟล์ + สถานะทดสอบ Group A/B/C แบบเดียวกับข้อ 2
    4. `session_logs/latest.md` — entry นี้เอง
- คำสั่ง: `python3 -c "...build_alignment_from_pi..."` (Group C ยืนยันฝั่ง Python),
  `node compare_groupC_clothoid.js` (scratchpad, Group C node-vs-python), `git diff --
  reference/Alignment.gs reference/AlignmentBuilder.gs` (ตรวจว่ายังว่างเปล่า — ไม่แตะ
  oracle เดิมแม้แต่บรรทัดเดียว)
- ผล: PASS ทุกจุด — Group A 9/9 ค่าตรง (Sheets), Group B ตรง (Sheets), Group C diff=0
  ทุก control point (Node-vs-Python เท่านั้น, ไม่ใช่ Sheets)
- commit: ยังไม่ commit — รอผู้ใช้ตรวจ diff ทั้ง 4 ไฟล์ครบก่อนตามคำสั่งชัดเจน ("ยังไม่ commit
  จนกว่าจะตรวจสอบครบทั้ง 4 ข้อ")
- หมายเหตุ:
  - พบจุด cosmetic ที่ยังไม่แก้: JSDoc header **บรรทัด 5** ของ `GS_AlignmentBuilder.gs` ยัง
    เขียนชื่อไฟล์เดิมว่า "AlignmentBuilderV2" (ค้างจากก่อน `git mv` ไป `reference/gsheet/`)
    ไม่กระทบการทำงานเพราะเป็นแค่ comment ไม่ใช่ชื่อ module/ตัวแปรจริง (module var เปลี่ยนเป็น
    `GS_AlignmentBuilder` ถูกต้องแล้วตั้งแต่ §2 ขั้นตอน 1-5) — อยู่นอกสโคปที่อนุมัติรอบนี้
    เก็บไว้เป็นรายการ cleanup รอสั่งแก้แยกใน session หน้า
  - เงื่อนไขก่อน commit ที่เหลือตามแผน (`pytest -q` ซ้ำ, `git diff` oracle ว่างเปล่า, commit
    message ผ่าน `.git\smt_commit_msg.txt`) ยังไม่ได้รันซ้ำในรอบนี้ (เอกสารเท่านั้น) — รอทำ
    ก่อน commit จริง

## [2026-07-13] พอร์ต GAS §2 เสร็จสมบูรณ์ — GS_AlignmentBuilder.gs curveSubs_ แก้แล้ว (ขั้นตอน 6-11)

- ทำ: ทำต่อจาก session_logs/plan_20260713_0257.md §2 เฉพาะขั้นตอน 6-11 ในรอบนี้
  (ขั้นตอน 1-5 ทำไปแล้วรอบก่อน — ดู entry ด้านล่าง)
  - ยืนยันสถานะก่อนเริ่ม: git status ตรงตามคาด (rename staged, GS_AlignmentBuilder.gs
    + session_logs/latest.md modified unstaged), `node -e "require(...)"` ผ่าน,
    `node reference/gsheet/smoke_test.js` ยังผ่าน 23/23
  - แก้ `curveSubs_` (reference/gsheet/GS_AlignmentBuilder.gs) แทนสูตรเชิงเส้น
    `thIn = LsIn/(2R)` / `thOut = LsOut/(2R)` ด้วย helper ใหม่ `spiralTurningAngle_(R, length, trans)`
    mirror `_spiral_turning_angle` (src/smt/builders/alignment_builder.py:139-150,
    commit ba5de3c) — เรียกผ่าน synthetic SPIN element + `exitState().az` (ไม่ใช่ `.azimuth`
    — ยืนยันซ้ำจาก GS_Alignment.gs ว่าทุก property state ชื่อ `az` เท่านั้น)
  - ใช้ `vert.transIn || vert.trans` / `vert.transOut || vert.trans` เป็น argument
    `trans` ให้ตรงกับ `subs.push` ที่ใช้อยู่แล้วในบล็อกเดียวกัน (ละเอียดกว่าคำสั่งเดิม
    ที่ระบุแค่ `vert.trans`)
  - ทดสอบเพิ่มก่อน save: เรียก `spiralTurningAngle_(R, L, undefined)` ตรงๆ ยืนยันว่า
    `GS_Alignment.makeElement` fallback `trans` เป็น `undefined` ไปเป็น `'CLOTHOID'` เสมอ
    (ไม่พังเงียบ) — ผลตรงกับ `trans='CLOTHOID'` เป๊ะ (diff=0) และตรงกับสูตรเชิงเส้นเดิม
    `L/(2R)` (diff ระดับ 1e-17 float noise)
  - ตรวจ EXT-001 patch 3 จุดเดิม (early-return บรรทัด 58-61, `names_` guard บรรทัด
    84-87, `buildFromPI` angle-point branch บรรทัด 131-141 — เลขบรรทัดขยับจากเดิม
    เพราะ header/require ยาวขึ้นจากขั้นตอน 4-5) ไม่ถูกแตะเลย ยืนยันด้วย git diff เต็มไฟล์
  - เขียน quick Node script เปรียบเทียบ `spiralTurningAngle_` กับ Python
    `_spiral_turning_angle` (เรียกตรงจาก src/smt/builders/alignment_builder.py ด้วย
    python3) ที่ 3 จุด: COSINE R=900/L=100, COSINE R=250/L=50, CLOTHOID R=500/L=80
    — **ผลตรงกันทุกบิต (diff=0.000e+0) ทั้ง 3 จุด**
  - save ไฟล์จริงหลังผ่านการตรวจครบ ยืนยัน byte-level ด้วย `git diff` ก่อนเสมอ
- คำสั่ง: `git status`, `node -e "require('./reference/gsheet/GS_AlignmentBuilder.gs')"`,
  `node reference/gsheet/smoke_test.js`, `python3 -c "from src.smt.builders...` (คำนวณ
  `_spiral_turning_angle` อิสระ 3 จุด), node script เปรียบเทียบ node-vs-python,
  `git diff -- reference/gsheet/GS_AlignmentBuilder.gs`, `pytest -q`
- ผล: PASS ทุกจุด
  - `node reference/gsheet/smoke_test.js` → 23 passed, 0 failed (ไม่มี regression
    จากการแก้ curveSubs_)
  - `pytest -q` → 493 passed (ไม่ได้แก้ไฟล์ Python เลยรอบนี้ — ยืนยันว่าไม่พลาดแก้ผิดที่;
    ตัวเลข 493 มากกว่า "407/407" ที่ CLAUDE.md บันทึกไว้เพราะมี test เพิ่มขึ้นตั้งแต่นั้น
    ไม่ใช่ regression)
  - Node-vs-Python: COSINE R=900/L=100 js=0.05548300509924253 python=0.05548300509924253
    diff=0; COSINE R=250/L=50 js=0.09957887368657481 python=0.09957887368657481 diff=0;
    CLOTHOID R=500/L=80 js=0.08000000000000007 python=0.08000000000000007 diff=0
- commit: ยังไม่ commit — git status ยืนยันว่ามีแค่ staged rename + unstaged
  modification ใน GS_AlignmentBuilder.gs และ session_logs/latest.md เท่านั้น
- หมายเหตุ:
  - พบ header comment (บรรทัด 28-29 เดิม) ยังเขียนว่า "curveSubs_ patch ยังไม่เสร็จ
    ณ commit นี้ — รอ session ถัดไป" ซึ่งล้าสมัยแล้วตอนนี้ (patch เสร็จแล้วรอบนี้) —
    ไม่ได้แก้เพราะอยู่นอกสโคปขั้นตอน 6-11 ที่อนุมัติ รอคำสั่งรอบหน้า
  - §2 เสร็จสมบูรณ์ทั้งหมดแล้ว (ขั้นตอน 1-11) — **ยังไม่ commit** และ **ยังไม่แตะ §5**
    (ทดสอบ Google Sheets จริง) ตามคำสั่งผู้ใช้ชัดเจน รอ session หน้าตัดสินใจ
    commit strategy + เริ่ม §5

## [2026-07-13] พอร์ต GAS §2 (บางส่วน) — GS_AlignmentBuilder.gs: git mv + rename + header (ยังไม่แก้ curveSubs_)

- ทำ: ทำตามแผน session_logs/plan_20260713_0257.md §2 เฉพาะขั้นตอน 1-5 ในรอบนี้
  (ขั้นตอน 6-11 ยังไม่ทำ รอ session หน้า)
  - ยืนยันซ้ำก่อนเริ่มว่า node reference/gsheet/smoke_test.js (§1) ยังผ่าน 23/23
    เหมือนเดิม และ grep AlignmentBuilderV2 ทั้ง repo ไม่พบ living reference อื่น
    นอกจากตัวไฟล์เอง (ตรงกับที่แผนแม่สรุปไว้)
  - git mv reference/AlignmentBuilderV2.gs -> reference/gsheet/GS_AlignmentBuilder.gs
    (เก็บ git history ด้วย rename ไม่ใช่ delete+add)
  - เปลี่ยนชื่อ module AlignmentBuilderV2 -> GS_AlignmentBuilder (var declaration
    + module.exports) และแก้ require path 3 บรรทัดบนสุดให้ถูกต้องหลังย้ายไฟล์:
    ./FPMath.gs -> ../FPMath.gs, ./WCB.gs -> ../WCB.gs, ./Alignment.gs ->
    ./GS_Alignment.gs (จุดที่แผนแม่ไม่ได้ระบุชัดคือ FPMath/WCB path ก็ต้องแก้เป็น
    ../ ด้วยเพราะไฟล์ย้ายลงไปอีกโฟลเดอร์ — พบระหว่างตรวจสอบตอนวางแผน ไม่ใช่ตอน execute)
  - เปลี่ยน Alignment. -> GS_Alignment. ทั้ง 7 จุดที่เรียก .makeElement/.exitState
    (บรรทัด 99, 101, 129, 149, 156, 159, 170) ยืนยันด้วย grep ว่าไม่มี "Alignment."
    เดี่ยวๆ (ไม่มี GS_ นำหน้า) หลงเหลือเลยสักจุด
  - อัปเดต header comment: คง EXT-001 (cdf896d) เดิมไว้ทั้งหมด เพิ่มย่อหน้าใหม่
    อ้างอิง EXT-003 (ba5de3c) ระบุชัดว่า curveSubs_ patch ยังไม่เสร็จ ณ commit นี้
    (ไม่ overclaim) และแก้บรรทัด "สร้างบน FPMath, WCB, Alignment" ที่ตกหล่นเป็น
    "GS_Alignment" ให้ตรงกับชื่อ dependency จริงหลังย้าย
  - ก่อนแก้ทุกจุด อ่าน curveSubs_ เต็มฟังก์ชันยืนยัน sign convention ของ R
    (บรรทัด 56 var R = Math.abs(vert.R) — absolute เสมอ) แยกจาก sgn (บรรทัด 118
    ใน buildFromPI) คนละ scope กันชัดเจน เทียบกับ Python
    (alignment_builder.py:91 R = abs(float(vert['R']))) โครงสร้างตรงกัน 100% —
    เตรียมไว้สำหรับขั้นตอน 6 (แก้ curveSubs_ ใส่ spiralTurningAngle_) ที่ยังไม่ทำ
    รอบนี้ ไม่มีความเสี่ยงสลับเครื่องหมายมุมเลี้ยว
- คำสั่ง: `node -e "require('./reference/gsheet/GS_AlignmentBuilder.gs')"` (ยืนยัน
  require ผ่านหลังแก้แต่ละขั้น), `node reference/gsheet/smoke_test.js` (regression
  check §1), `git status` / `git diff --stat`
- ผล: PASS — require ไม่มี error, smoke test §1 ยังผ่าน 23/23 เหมือนเดิมทุกครั้งที่
  ตรวจหลังแก้ ยังไม่ได้รัน pytest -q รอบนี้ (ยังไม่แตะ Python เลย)
- commit: ยังไม่ commit — git status ยืนยันว่ามีแค่ staged rename +
  unstaged modification ใน GS_AlignmentBuilder.gs และ session_logs/latest.md
  เท่านั้น ไม่มี commit เกิดขึ้นเลยรอบนี้
- หมายเหตุ: หยุดตามคำสั่งผู้ใช้ที่ขั้นตอน 1-5 ของ §2 รอบนี้ (session เหลือน้อย) —
  ขั้นตอน 6 (แก้ curveSubs_ ใส่ spiralTurningAngle_ แทนสูตรเชิงเส้น thIn/thOut),
  7 (quick Node-vs-Python test), 8 (save curveSubs_), 9 (pytest -q), 10 (log
  entry สรุป §2 เต็ม), 11 (จบรอบ) และ §5 (ทดสอบ Google Sheets จริง) ยังไม่เริ่ม
  รอทำต่อ session หน้า อ้างอิงแผนเดิม session_logs/plan_20260713_0257.md และ
  plan file ของรอบนี้ที่ C:\Users\CK1024\.claude\plans\session-logs-plan-20260713-0257-md-2-gs-luminous-wall.md
  (มีรายละเอียด sign-convention verification ของ R/sgn ที่ตรวจไว้แล้ว พร้อมใช้ต่อ
  ในขั้นตอน 6)

## [2026-07-13] พอร์ต GAS Phase 1 — GS_Alignment.gs (COSINE closed-form) + smoke test

- ทำ: ทำตามแผน session_logs/plan_20260713_0257.md (เฉพาะ §1 และ §4 รอบนี้)
  - สร้าง reference/gsheet/GS_Alignment.gs ใหม่ (copy จาก reference/Alignment.gs
    oracle 268 บรรทัด ตรวจแล้วว่า 11 ฟังก์ชัน "copy ตรง" ตรงกับ oracle 100%
    byte-for-byte) เพิ่ม COSINE (Civil 3D Sine Half-Wave) closed-form +
    arc-length inversion mirror จาก src/smt/alignment.py (หลัง commit
    ba5de3c) ใช้ Map แทน lru_cache ตามที่ investigation ยืนยันว่าใช้ได้จริงใน
    GAS V8 runtime — ไม่แตะ reference/Alignment.gs เดิมเลยแม้แต่บรรทัดเดียว
    (ยืนยันด้วย diff ก่อน commit)
  - เขียน reference/gsheet/smoke_test.js ครอบคลุม 3 จุด ground truth
    (R=900/L=100, R=250/L=50, R=500/L=70) x 3 ค่า (totalX/theta/totalY)
    = 9 ค่า, SPIN/SPOUT theta symmetry, cache sharing, regression
    CLOTHOID/BLOSS/SINE
  - ระหว่างทดสอบพบ 2 บั๊กในตัว test เอง (ไม่ใช่บั๊กใน GS_Alignment.gs):
    (1) cache test เดิมใช้ R=900/L=100 ซ้ำกับจุดที่ Test 2 (SPOUT) แคชไปแล้ว
    เป็น side-effect ทำให้ assertEqual เพี้ยน แก้เป็น R=333/L=44 ที่ไม่ซ้ำ
    กับจุดใดเลยในไฟล์ (2) Test 2 เดิม assert ว่า SPIN/SPOUT ต้องได้ totalY
    เท่ากัน ซึ่งไม่จริงตามธรรมชาติสูตร (SPOUT วัด y จากกรอบอ้างอิงคนละจุดกับ
    SPIN) พิสูจน์ด้วยการรัน python เทียบ src/smt/alignment.py โดยตรงว่า GS
    กับ Python ให้ค่า SPOUT e ตรงกันบิตต่อบิต ยืนยันว่าไม่ใช่บั๊กพอร์ต แก้
    test ให้เหลือแค่ assert theta เหมือน
    tests/test_alignment.py::test_cosine_spin_spout_symmetry_matches_civil3d
    จริง
- คำสั่ง: node reference/gsheet/smoke_test.js (รันจากตำแหน่งจริงใน reference/gsheet/ ไม่ใช่ scratchpad)
- ผล: PASS (23/23 assertion ผ่านหมด)
- commit: ยังไม่ commit — ยังไม่ผ่านเงื่อนไข pre-commit gate ของแผน (ต้องทำ §2
  GS_AlignmentBuilder.gs และ §5 ทดสอบ Google Sheets จริงให้เสร็จก่อน)
- หมายเหตุ: หยุดตามคำสั่งผู้ใช้ที่ §1+§4 รอบนี้ — §2 (GS_AlignmentBuilder.gs,
  git mv จาก reference/AlignmentBuilderV2.gs + แพตช์ turning-angle) และ §5
  (ทดสอบ Google Sheets จริง) ยังไม่เริ่ม รอทำต่อ session หน้า อ้างอิงแผนเดิม
  session_logs/plan_20260713_0257.md

## [2026-07-12] แก้ SMT_WCBatSta ให้ delegate ผ่าน SMT_SolveForward/SMT_PointOnElement + แก้ ByRef compile error

- ทำ: พบระหว่างทดสอบ Excel ว่า SMT_WCBatSta คำนวณ theta ผิดสำหรับ COSINE (และ
  BLOSS/SINE ที่จุดกลางโค้งมานานแล้วก่อนหน้า Phase 4 ด้วย) เพราะเป็นฟังก์ชันแยกที่
  เขียนสูตรมุมเอง ไม่เคยเรียก SMT_PointOnElement เลย ไม่อ่านคอลัมน์ Transition เลย
  ด้วยซ้ำ แก้ตามแผน session_logs/plan_vba_wcbatsta_delegate_fix.md (Option B):
  - ขยาย SMT_SolveForward ให้คืนค่า tangent azimuth เป็น element ที่ 3 (res(2))
  - เขียน SMT_WCBatSta ใหม่ให้ delegate ผ่าน SMT_SolveForward แทนสูตรมุมเอง
  - แก้ ByRef compile error ที่พบภายหลัง (ส่ง pt(2) ตรงๆ ให้ SMT_NormalizeAngle
    ไม่ได้ ต้องผ่านตัวแปร Double คั่นกลางก่อน)
  - อัปเดต comment block "Expected values" ท้ายไฟล์ เพิ่มตัวอย่าง COSINE ที่
    ยืนยันแล้ว
  - พิสูจน์พีชคณิตแล้วว่า T, C, SPIN/SPOUT-CLOTHOID ให้ผลเท่ากันทุกประการกับสูตร
    เดิม (ผู้ใช้ยืนยันซ้ำด้วย sympy อิสระ)
  - ทดสอบ Excel จริงผ่านครบ 17 จุด (3 COSINE + 10 BLOSS/SINE mid-curve + 1
    boundary จาก test_data/SettingOutTest.csv จริง ผ่าน build_alignment_from_pi
    + 3 T/C/CLOTHOID spot-check) ตรงกับ Python engine ทุกจุดในระดับ
    floating-point noise
  - grep ยืนยันฝั่ง Python (alignment.py, alignment_builder.py) ไม่มีสูตรแยกซ้ำ
    แบบเดียวกัน ปลอดภัย
- คำสั่ง: git add -p (hunk-level เฉพาะส่วน WCBatSta fix + plan file) ->
  git commit -F .git\smt_commit_msg.txt
- ผล: PASS — Excel 17/17 จุดผ่าน
- commit: `ba5de3c`
- หมายเหตุ: บั๊กนี้เป็นบั๊กเดิมที่มีมาก่อน Phase 4 (ไม่ใช่ผลจาก Phase 4) แค่ถูก
  ค้นพบระหว่างทดสอบ Phase 4

## [2026-07-12] Phase 4 — port COSINE closed-form + arc-length inversion to SMT_Alignment.bas

- ทำ: apply diff ตามแผนที่อนุมัติ (plan mode) — เพิ่ม SMT_SINE_HALFWAVE_C constant,
  5 ฟังก์ชันใหม่ (SMT_CosineDydx, SMT_CosineArcLength, SMT_CosineSolveA,
  SMT_CalcSineHalfwaveTangentLength, SMT_SineHalfwavePoint) mirror
  src/smt/alignment.py หลัง commit d8ebedd, เพิ่ม branch ใหม่ใน SMT_PointOnElement
  ดักจับ COSINE pure SPIN/SPOUT ก่อนถึง Simpson path เดิม, แก้ header comment ให้
  ตรงกับ implementation ใหม่ ไม่ทำ cache (Scripting.Dictionary) รอบแรกตามที่
  ตัดสินใจไว้ (Excel UDF ไม่ได้เรียกถี่เท่า Python build pipeline)
- คำสั่ง: Edit tool ตาม diff ที่อนุมัติทีละจุด -> git add -p (hunk-level เฉพาะ
  ส่วน COSINE port) -> git commit -F .git\smt_commit_msg.txt
- ผล: PASS (ยืนยันด้วย git diff --cached ก่อน commit ว่า stage ตรงตามที่ต้องการ)
- commit: e285fd5
- หมายเหตุ: ระหว่างทดสอบ Excel รอบแรกพบว่า SMT_WCBatSta ยังผิด เพราะเป็นฟังก์ชัน
  แยกที่ไม่ผ่าน SMT_PointOnElement เลย ไม่ใช่ผลจาก diff รอบนี้ แต่เป็นบั๊กเดิมที่
  มีมาก่อน — แก้แยกเป็นอีก commit (ดู entry ก่อนหน้า)

## [2026-07-12] สืบสวน Phase 4 — ขอบเขตอัปเดต VBA COSINE (plan mode, ยังไม่แก้โค้ด)

- ทำ: สืบสวนสโคป Phase 4 (อัปเดต reference/vba/SMT_Alignment.bas ให้ตรงกับ core engine
  ปัจจุบันหลัง commit d8ebedd) เทียบโค้ด VBA SMT_ShapeIntegral/SMT_TurningAngle/
  SMT_PointOnElement กับ src/smt/alignment.py ทีละจุด พบว่า VBA ยังตรงกับ Python เวอร์ชัน
  ก่อน COSINE closed-form fix รอบแรก (2026-07-05) คือตกทั้ง 2 รอบที่เกี่ยวข้อง (closed-form +
  arc-length inversion) ไม่ใช่แค่ตกรอบ arc-length inversion เดียว
  - ระบุ error จริง: ~2.90-4.71 ซม. จากไม่มีสูตรปิด (ก้อนหลัก), 1.55-4.53 มม. เพิ่มเติมจากไม่มี
    arc-length inversion (ก้อนรอง)
  - พบว่า Simpson quadrature และ bisection ซึ่งเป็นแกนของ arc-length inversion มีต้นแบบอยู่แล้ว
    ในไฟล์ SMT_Alignment.bas เอง (ความเสี่ยง port ต่ำ) จุดเสี่ยงจริงคือไม่มี cache เทียบเท่า
    lru_cache ใน VBA เลย ต้องออกแบบ Scripting.Dictionary ใหม่
  - ยืนยัน blast radius จำกัดแค่ SMT_Alignment.bas ไฟล์เดียว (grep ไม่พบ COSINE/shape-integral
    ใน SMT_Vertical.bas, SMT_Crossfall.bas, SMT_Geometry.bas, SMT_Core.bas เลย)
  - ยืนยันไม่มี automated test harness สำหรับ VBA เลย มีแค่ comment block "Expected values" —
    ต้องยืนยันด้วยมือใน Excel จริงเมื่อแก้จริง
  - ผู้ใช้ตรวจตัวเลขสำคัญ (494x, 2.27e-06 ถึง 4.23e-05 องศา) แล้วตรงกับที่พิสูจน์ไว้ก่อนหน้า อนุมัติ
    ให้ save
- คำสั่ง: อ่านไฟล์ตรงๆ (Read/Grep) เทียบ reference/vba/*.bas กับ src/smt/alignment.py +
  session_logs/investigate_sinehalfwave_formula.md + investigate_cosine_arclength_inversion.md
- ผล: PASS — รายงานสืบสวนเสร็จสมบูรณ์ ไม่มีการรัน test เพราะไม่มีการแก้โค้ด
- commit: (รอ — แสดง commit message ให้ตรวจก่อน)
- หมายเหตุ: ยังไม่มีแผนแก้ SMT_Alignment.bas จริง ต้องรอ Plan-Review-Approve รอบใหม่ก่อนลงมือ

## [2026-07-11] Execute Phase 3 — regenerate golden fixture, commit Phase 1+3 together

- ทำ: execute แผน Phase 3 (session_logs/investigate_phase3_golden_regen_scope.md, commit 13b02e7)
  - เขียนสคริปต์ regenerate ใน scratchpad (ไม่ commit) เรียก _make_vertices + build_alignment_from_pi
    ตามกลไกเดิม แก้ 2 จุดตามที่ผู้ใช้สั่งก่อนรัน: radius เก็บเครื่องหมายจริง (ไม่ใช้ abs()), เขียนไฟล์
    ด้วย CRLF ไม่มี trailing newline ให้ตรงกับ format เดิม
  - dry-run diff เต็ม พบว่า element/control นอกกลุ่ม COSINE (index 1-10, 15-29) ก็มี diff ระดับ
    ~1e-4m/~0.02-0.03 arcsec ด้วย (กว้างกว่า hard-stop gate เดิมที่เขียนไว้ในแผน) ตรวจสอบแล้วว่าไม่ใช่
    ผลจาก Phase 1 จริง (Group 4 test ยืนยัน CLOTHOID/BLOSS/SINE byte-identical) จึงเป็น noise พื้นฐาน
    จาก _make_vertices reconstruction ที่มีอยู่แล้ว — ผู้ใช้อนุมัติ apply หลังตรวจตัวเลขนี้
  - apply จริงทับ tests/golden/tables.json + reference/tables.json → byte-compare สองไฟล์ identical
    → pytest -q ได้ 490 passed, 0 failed ตรงเป้าเป๊ะ
  - เพิ่ม addendum ใน investigate_phase3_golden_regen_scope.md แก้คำอธิบาย hard-stop gate ที่เขียน
    แคบเกินจริงในแผน execute เดิม (ไม่ได้เผื่อ noise พื้นฐานทุกกลุ่มไว้) พร้อมเหตุผลพิสูจน์ได้ (Group 4
    test) ไม่ใช่แค่ตัวเลขตรงกับรายงานเดิม
  - ตัดสินใจ commit strategy (คำถามเปิดจากแผน Step 6): รวม Phase 1 + Phase 3 เป็น commit เดียว รวมทั้ง
    session_logs/plan_cosine_arclength_core_fix.md (Phase 1 plan, untracked มาก่อน) และ
    investigate_phase3_golden_regen_scope.md addendum เข้าด้วยกัน — ไม่รวม test_data 2 ไฟล์ที่ไม่
    เกี่ยวข้อง (ยัง untracked ต่อไป)
- คำสั่ง: python regenerate script (dry-run แล้ว --apply) → `diff -q` byte-compare → `pytest -q` →
  Write .git\smt_commit_msg.txt → git add (6 ไฟล์เจาะจง) → git commit -F
- ผล: PASS — 490 passed, 0 failed (ตรงเป้าที่กำหนดไว้ทุกประการ), byte-identical ยืนยันแล้ว
- commit: (รอ — แสดง commit message ให้ตรวจก่อน)

## [2026-07-11] สืบสวน Phase 3 — ขอบเขตการ regenerate golden fixture (plan mode, ยังไม่แก้โค้ด)

- ทำ: สืบสวนก่อนวางแผน Phase 3 (regenerate tests/golden/tables.json + reference/tables.json
  ให้ตรงกับ Phase 1 ที่แก้ core engine COSINE arc-length inversion — plan_cosine_arclength_core_fix.md)
  - ยืนยัน git status/diff ตรงกับที่คาด (206/-55 บน alignment.py + test_alignment.py)
  - ตรวจ alignment_builder.py ยืนยันว่า `_spiral_turning_angle`/`_calculate_end_displacement`
    เรียก `calculate_exit_state` ตรงๆ อยู่แล้ว — ไม่ต้องแก้โค้ด builder เพิ่มเลย รับผล Phase 1
    อัตโนมัติ
  - รัน pytest จริง: 9 failed, 481 passed — ยืนยัน single root cause (COSINE curve group เดียว
    R=500/L=70 ที่ SC/CS gap ~31mm ตรงกับ L-X ที่ทำนายไว้ในแผน Phase 1)
  - เทียบขอบเขตกับ 2 รอบ regenerate ก่อนหน้า: รอบนี้แคบกว่าในแง่ N,E ที่เปลี่ยนจริง (1 ใน 9 กลุ่ม)
    แต่กว้างกว่าในแง่คอลัมน์ station (18 จาก 30 element rows ต้องเขียนทับเพราะ station สะสมต่อกัน)
  - **ยังไม่มีการแก้โค้ดใดๆ ในรอบนี้** — เป็นรายงานสืบสวนล้วน ไม่ได้เขียนแผนแก้
- คำสั่ง: `git status`, `git diff --stat`, `pytest -q`, `pytest -v` (9 ตัวที่ fail แยกทีละตัว),
  python สคริปต์เทียบ `_make_vertices`+`build_alignment_from_pi` กับ golden fixture จริง →
  Write session_logs/investigate_phase3_golden_regen_scope.md
- ผล: PASS (ไม่มีการแก้โค้ด — งานสืบสวน/รายงานล้วน; pytest ปัจจุบัน 9 failed, 481 passed ตามที่คาด)
- commit: (รอ — ยังไม่ commit ไฟล์รายงานนี้)

## [2026-07-07] สืบสวน COSINE totalY/theta/tanShort ใน LandXML export — สรุปว่าตกกรณียาก

- ทำ: สืบสวน (plan mode, ยังไม่แก้โค้ด) ว่าทำไม theta/totalY/tanShort ของ COSINE ใน LandXML
  export ยังใช้ค่าประมาณ ไม่ตรง Civil 3D จริง แม้ totalX แก้ไปแล้วก่อนหน้านี้
  - ยืนยันด้วย Explore agent 2 ตัว + คำนวณ python จริง: ตัวเลขส่วนต่างตรงกับที่บันทึกไว้เดิม
    ทุกตัว (0.0017762° ที่ R=900/L=100, 0.0102878° ที่ R=250/L=50)
  - พบว่า theta คือ `calculate_exit_state(...).azimuth` ตัวเดียวกับที่ใช้วาง element ถัดไปจริง
    ในไฟล์ (ต่างจาก totalX ซึ่งเป็นตัวเลขบรรยายเดี่ยวไม่มีใครพึ่งพา)
  - สรุป: **ตกกรณียาก** — ถ้าจะแก้ให้ตรงจริงต้องแก้ core engine
    (`calculate_point_on_element`/`calculate_exit_state` ใน alignment.py) ไม่ใช่แค่ patch
    landxml.py แบบเดียวกับ totalX เพราะจะทำให้ theta ไม่ตรงกับพิกัด End/azimuth ที่ element
    ถัดไปใช้จริงในไฟล์เดียวกัน (ไฟล์ขัดแย้งในตัวเอง) การแก้จริงจะกระทบ golden fixture ทั้งชุด
    และต้องอัปเดต VBA คู่กันตามกฎ
  - **ยังไม่มีการแก้โค้ดใดๆ ในรอบนี้** — เป็นรายงานสืบสวนล้วน
- คำสั่ง: Explore agent ×2 (parallel) → python3 -c คำนวณยืนยันตัวเลข → เขียนร่างลง scratchpad
  → cat แสดงให้ตรวจ → ผู้ใช้อนุมัติ → Write session_logs/investigate_cosine_totaly_theta_export.md
  → diff เทียบ scratchpad กับไฟล์จริง (ไม่ต่างกันเลย)
- ผล: PASS (ไม่มี test เกี่ยวข้อง — งานสืบสวน/เอกสารล้วน ไม่แตะโค้ด)
- commit: (รอ — จะ commit เฉพาะ investigate_cosine_totaly_theta_export.md + latest.md ต่อจากนี้)

## [2026-07-07] Annotate oracle ใน reference/Alignment.gs

- ทำ: เพิ่ม comment เตือน 5 บรรทัดเหนือ case COSINE ในฟังก์ชัน shapeIntegral_ อธิบายว่าเป็น
  จุดอ้างอิงประวัติศาสตร์ที่แช่แข็งไว้ ไม่ตรงกับ Civil 3D จริง ชี้ไปที่ docs/extensions.md
  EXT-003 และ alignment.py แทน
  ไม่แก้สูตรหรือค่าใดๆ ในไฟล์ ตามหลัก frozen oracle
- คำสั่ง: diff เทียบก่อน/หลังคัดลอกทับ → git diff -- reference/Alignment.gs (ยืนยัน 5 บรรทัด
  comment เท่านั้น) → Write .git\smt_commit_msg.txt → git add reference/Alignment.gs →
  git commit -F .git\smt_commit_msg.txt → git push
- ผล: PASS (ไม่มี test เกี่ยวข้อง — เอกสาร/comment ล้วน ไม่แตะโค้ด)
- commit: 1818a38 (push แล้ว c3b535c..1818a38)

## [2026-07-06] เพิ่ม chord/delta/tangent/external/midOrd/crvType และ PI sub-tag ให้ Curve/Spiral ใน LandXML export

- ทำ: สืบสวนสูตรเทียบ Civil 3D ground truth จริง (จากไฟล์ C3D_Export_SMT_TEST_CLOTHOID.xml
  ที่ผู้ใช้ทดสอบ) พบว่าตรงกันในระดับ 0.008-0.30 มม. ไม่ใช่ตรงเป๊ะ (คาดว่า Civil 3D คำนวณ
  geometry ใหม่เองหลัง import)
  - เพิ่ม 6 attribute ให้ Curve และ PI sub-tag ให้ทั้ง Curve และ Spiral (SPIN/SPOUT) โดยใช้
    wcb.calculate_forward ที่มีอยู่แล้ว
  - พบและปิดช่องโหว่ระหว่างวางแผน คือ PI point ของ SPOUT ไม่มี ground truth อิสระให้เทียบ
    (มีแค่ SPIN) จึงเพิ่ม test แยกสำหรับ SPOUT ด้วย self-consistency + mirror-symmetry แทน
    ระบุข้อจำกัดนี้ไว้ชัดเจนในเอกสารและ docstring
  - เพิ่ม 6 test ใหม่ (รวม geometric invariant test ที่ไม่พึ่ง ground truth) ยืนยันด้วย
    smoke test จริงผ่าน SettingOutTest.csv (10 Curve + 10 Spiral ไม่มีปัญหา)
  - ระหว่างทางยังพิสูจน์ยืนยันว่า SMT export-landxml ทำงานได้จริงกับ Civil 3D 2023 จริง
    (import ผ่านเมนู Insert เขียน LandXML มาตรฐาน) ซึ่งเป็นการยืนยันครั้งแรกในโปรเจกต์ว่าไฟล์
    export ใช้งานได้จริง ไม่ใช่แค่ตัวเลขตรงกับ ground truth
- คำสั่ง: สืบสวน → วางแผน → แก้โค้ด/เทส → pytest -q → smt export-landxml smoke test →
  Write .git\smt_commit_msg.txt → git add → git commit -F (แยกกันตามลำดับงาน)
- ผล: PASS 467/467
- commit: cd9d138 (สืบสวน), c3b535c (แผน+โค้ด+test)

## [2026-07-05] แก้ LandXML COSINE totalX รายงานค่า L แทนค่า X ปิดที่ถูกต้อง

- ทำ: สืบสวนพบว่า _sine_halfwave_point คืนค่า x ที่รับเข้ามาตรงๆ ไม่แปลงเป็นค่า X ปิด ทำให้
  totalX ที่ export ออกไปเท่ากับ L เป๊ะ
  - แก้โดยเพิ่มฟังก์ชันสาธารณะ calculate_sine_halfwave_tangent_length ใน alignment.py
    (จุดความจริงเดียว ใช้ทั้งใน alignment.py เองและ landxml.py) แก้เฉพาะ totalX ของ COSINE
    เท่านั้น ไม่แตะ totalY หรือ theta
  - เพิ่ม 2 test ใหม่ใน test_landxml.py ยืนยันด้วย smoke test จริงผ่าน SettingOutTest.csv
- คำสั่ง: สืบสวน → วางแผน → แก้โค้ด/เทส → pytest -q → smt export-landxml smoke test →
  Write .git\smt_commit_msg.txt → git add → git commit -F
- ผล: PASS 461/461
- commit: 5f70111 (สืบสวน+แผน), af5f849 (โค้ด+test)

## [2026-07-05] สำรวจ+จัดกลุ่ม CSV ใน test_data แล้วรัน smt build เฉพาะ PI table — audit เท่านั้น

- ทำ: ทำตามแผน `csv-test-data-dynamic-wigderson.md` (plan mode) — งานสำรวจล้วน ไม่แก้ไฟล์ใดๆ
  1. ลิสต์ CSV ทั้งหมดใน `test_data/` (ไม่รวม `build_out*`) ด้วย Glob — พบ 8 ไฟล์
  2. อ่าน header แต่ละไฟล์ จัดกลุ่มตามกฎที่กำหนด: `pi_compound_curve.csv`,
     `ramp01n01_SO.csv`, `ramp01n01_SO2.csv`, `SettingOutTest.csv` = PI table;
     `elements_output.csv`, `r01n01_elements_output.csv` = element table;
     `r01n01_so_crosscheck.csv` = drawing control point; `Bulk_cross-check.csv` = other
     (header เป็น POINT,N,E,Z,DISC — ไม่เข้าเกณฑ์ field survey เพราะคอลัมน์แรกไม่ใช่ NAME ตรงตัว
     ตามกฎ literal ที่กำหนด)
  3. รัน `smt build` กับ 4 ไฟล์ PI table เขียน output ไปที่ scratch folder นอก test_data
     (scratchpad ของ session นี้ — ไม่ใช่ `/tmp`)
- คำสั่ง: `smt build test_data/<file>.csv --out-dir <scratch>/<file>` × 4 → ตรวจ exit
  code + ไฟล์ output → ลบ scratch folder ทั้งหมด → `git status -sb` ยืนยัน test_data ไม่เปลี่ยน
- ผล: PASS ทั้ง 4 ไฟล์ — exit code 0 ทุกไฟล์ ไม่มี ValueError จาก `_flush_pending` defensive
  check เลย (ไม่มีข้อความ "มีทั้งค่า RADIUS...และมี compound sub-row ตามมา" ปรากฏ) ไม่มี
  warning อื่นบน stderr ด้วย — ยังไม่พบไฟล์ไหนที่เข้าข่ายบั๊กแบบเดียวกับ PI7 เดิม
- commit: ไม่มี (งาน audit ล้วน ไม่มีไฟล์ให้ commit — scratch folder ลบทิ้งหมดแล้ว)
- หมายเหตุ: `Bulk_cross-check.csv` จัดเป็น "other" ตามกฎ literal header ที่ผู้ใช้กำหนด แม้
  โครงสร้างจะคล้าย field survey (N,E,Z,DISC) เพราะคอลัมน์แรกชื่อ POINT ไม่ใช่ NAME — ยังไม่ตัดสินใจ
  แทนผู้ใช้ว่าควรจัดกลุ่มใหม่หรือไม่ รอคำสั่ง

## [2026-07-05] สรุปรวม: แก้ COSINE closed-form + regenerate golden fixture (ปิดงานสองแผน)

- ทำ: ครบทั้ง 2 แผนที่เกี่ยวข้องกัน
  แผนที่หนึ่ง (session_logs/plan_cosine_sinehalfwave_fix.md):
  1. แก้ `src/smt/alignment.py` — COSINE ใช้สูตรปิด Civil 3D Sine Half-Wave แทน Simpson
     เดิม ทั้ง SPIN (สูตรตรง) และ SPOUT (mirror ผ่าน s↔L−s) พร้อมอัปเดต docstring
  2. เพิ่ม 3 test ใหม่ (ground truth R=900/L=100, R=250/L=50, symmetry SPIN/SPOUT) — PASS
  3. Mark xfail(strict=True) 9 ตัวที่ยังผูกกับ golden fixture เดิม (Simpson-based)
  4. Smoke test `smt export-landxml` จริง — ยืนยัน landxml.py ไม่ต้องแก้ พบ known
     limitation ใหม่ (`_build_curve_sub_elements` สมมติ theta เชิงเส้นผิดสำหรับ COSINE)
     บันทึกแยกไว้ใน session_logs/investigate_cosine_builder_mismatch_20260705.md

  แผนที่สอง (session_logs/report_xfail_mismatch_20260705.md + งาน regenerate):
  5. ตรวจผลจริงของ xfail 9 ตัว พบว่า 3 ตัวคาดผิด (pass จริง) และมี 1 ตัวใหม่ที่พังจริง
     โดยไม่คาดคิด (station คลาดเคลื่อน 8.4 ซม. ผ่าน `_calculate_end_displacement`) —
     สรุปจริง 9 ตัว (ไม่ใช่ 10 ตามที่ประเมินตอนแรก)
  6. เขียนสคริปต์ regenerate (`regenerate_cosine_golden_fixture.py`, scratchpad, ไม่ commit)
     dry-run แสดง diff เต็มให้ตรวจก่อน แล้วจึง apply จริงกับ `tests/golden/tables.json`
     และ `reference/tables.json` (20 element rows + 20 control rows เปลี่ยน, เหมือนกัน
     ทุกตัวอักษรทั้งสองไฟล์)
  7. ลบ xfail ออก 7 ตัวที่ fixture ใหม่แก้ตรงแล้ว แต่พบว่าเหลือ 2 ตัว
     (`test_chain_has_no_gaps`, `test_exit_state_matches_next_entry`) ยังพังจริงจาก
     สาเหตุใหม่: mismatch ของ `_build_curve_sub_elements` ที่เคยพบตอน smoke test ติดเข้าไป
     ในตัวเลขคงที่ของ fixture เองด้วย (ช่องว่าง 34.26 arcsec ที่รอยต่อ SPOUT-COSINE
     ยืนยันด้วย 2 วิธีอิสระตรงกันถึงหลักที่ 6) — mark xfail ใหม่ 2 ตัวนี้พร้อมเหตุผลที่ถูกต้อง
     แทนเหตุผลเดิม อัปเดต investigate_cosine_builder_mismatch_20260705.md และ CLAUDE.md
- คำสั่ง: แก้โค้ด/เทส → `pytest -q` → `smt export-landxml` → เขียน/รัน regenerate script
  (dry-run แล้ว apply) → `pytest -q` → Write `.git\smt_commit_msg.txt` → `git add` → `git commit -F`
  (4 ครั้งแยกกันตามลำดับงาน)
- ผล: PASS — สถานะสุดท้าย `455 passed, 2 xfailed, 0 failed` (ลดจาก 9 xfail เหลือ 2 ตัว
  ที่มีเหตุผลยืนยันแน่นอนแล้ว ไม่ใช่ของค้างที่ยังไม่ตรวจ)
- commit: 301245c (แก้ COSINE core + tests + xfail 9 + report), db39b85 (บันทึก known
  limitation builder mismatch), 162ef98 (session log), aa8038c (regenerate fixture +
  ลบ xfail 7 + เพิ่ม xfail ใหม่ 2 พร้อมเหตุผลที่ยืนยันแล้ว)
- หมายเหตุ: งานค้างที่ยังไม่วางแผน — แก้ `_build_curve_sub_elements` ให้รองรับทุก
  transition shape (ไม่ใช่แค่ COSINE) เพื่อลบ xfail 2 ตัวสุดท้ายได้ในที่สุด ยังไม่มีแผนแยก
  สำหรับงานนี้

## [2026-07-05] แก้ COSINE transition ให้ใช้สูตรปิด Civil 3D Sine Half-Wave (แผนหลัก)

- ทำ: ทำตาม session_logs/plan_cosine_sinehalfwave_fix.md ที่อนุมัติแล้วเต็มขั้นตอน
  1. แก้ `src/smt/alignment.py` — เพิ่ม `_SINE_HALFWAVE_C`, helper `_sine_halfwave_point`,
     branch ใหม่ใน `calculate_point_on_element` สำหรับ COSINE ทั้ง SPIN (ใช้สูตรตรง) และ
     SPOUT (mirror ผ่าน s↔L−s แบบเดียวกับ CLOTHOID/BLOSS/SINE) แทน Simpson integration เดิม
     พร้อมอัปเดต module docstring ส่วน Transition shapes + Known limitations ให้ครบ
  2. เพิ่ม 3 test ใหม่ใน `tests/test_alignment.py`: ground truth R=900/L=100, R=250/L=50
     (เทียบที่ d เท่ากับ X จุดที่สูตรตรง Civil 3D ระดับ machine precision) และ test สมมาตร
     SPIN/SPOUT (parametrize 3 คู่ R,L) — ทั้งหมด PASS
  3. ค้นและ mark xfail(strict=True) ให้ test ที่ผูกกับ golden fixture เดิม (Simpson-based)
     ที่ SC/ST ขยับ ~3 ซม. ตอนแรกคาด 10 ตัว รันจริงแล้วพบว่า 3 ตัว pass จริง (มีเหตุผล
     เฉพาะเจาะจงต่อตัว ไม่ใช่ fluke) และมี 1 ตัวใหม่ที่พังโดยไม่คาดคิด (station คลาดเคลื่อน
     8.4 ซม. ผ่าน _calculate_end_displacement ใน alignment_builder.py คูณด้วย 1/sin(δ))
     สรุปสุดท้าย mark จริง 9 ตัว บันทึกละเอียดใน session_logs/report_xfail_mismatch_20260705.md
  4. Smoke test `smt export-landxml` จริงกับไฟล์ทดสอบ R=900/L=100 และ R=250/L=50 —
     ยืนยัน landxml.py ไม่ต้องแก้โค้ด (delegate ผ่าน alignment.py อยู่แล้ว) แต่พบ known
     limitation ใหม่ระหว่างทาง: `alignment_builder.py::_build_curve_sub_elements` สมมติ
     มุมเลี้ยว spiral แบบเชิงเส้น (Ls/(2R)) ซึ่งไม่ตรงกับ COSINE closed-form ใหม่ ทำให้กลุ่มโค้ง
     COSINE ที่สร้างผ่าน build_alignment_from_pi คลาดเคลื่อน ~0.005 องศา บันทึกไว้ใน
     session_logs/investigate_cosine_builder_mismatch_20260705.md + CLAUDE.md Known limits
     ยังไม่แก้ อยู่นอกขอบเขตแผนนี้ รอวางแผนแยกภายหลัง
- คำสั่ง: แก้โค้ด/เทส → `pytest -q` → `smt export-landxml` (2 ไฟล์ทดสอบ) → เขียนรายงาน →
  Write `.git\smt_commit_msg.txt` → `git add` (เฉพาะไฟล์ที่เกี่ยวข้อง) → `git commit -F` (2 ครั้งแยกกัน)
- ผล: PASS — `448 passed, 9 xfailed` (ยืนยันด้วย `pytest -rx` ว่าตรงกับ 9 mark ที่ตั้งใจไว้ทุกตัว)
- commit: 301245c (แก้ COSINE core + xfail + report), db39b85 (บันทึก known limitation ใหม่จาก builder)
- หมายเหตุ: งานต่อเนื่องที่ผูกพันไว้แล้วคือ regenerate tests/golden/tables.json +
  reference/tables.json ให้ตรงสูตรใหม่ (ต้องแสดงแถวดิบเต็มให้ตรวจก่อนแก้ไฟล์ ตามที่ตกลงไว้ใน
  plan) และแก้ `_build_curve_sub_elements` ให้รองรับ COSINE closed-form (ยังไม่ได้วางแผน)

## [2026-07-05] บันทึกหลักฐาน SPIN/SPOUT mirror-symmetry เพิ่มในรายงาน COSINE — รายงานเท่านั้น

- ทำ: เปิด plan mode ชั่วคราวสำหรับงานบันทึกเดียว (ตามกฎ CLAUDE.md งานอ่าน/รายงานไม่ต้องผ่าน
  Plan-Review-Approve) ต่อท้าย `session_logs/investigate_sinehalfwave_formula.md` ด้วยหลักฐาน
  Civil 3D จริงที่อาจารย์ยกมา (R=250 L=50 จาก SMT_TEST_ALINGMENT2.xml ก่อนไฟล์หาย): SPIN กับ
  SPOUT ที่ R,L เท่ากัน ให้ theta/totalX/totalY/tanLong/tanShort เท่ากันทุกตัวเป๊ะ ยืนยัน
  mirror-symmetry ด้วยข้อมูลจริง ไม่ใช่ข้อสันนิษฐาน — ใช้แนวทาง swap k_in/k_out ผ่าน s↔L−s บน
  ฟังก์ชันเดียวกัน (แบบเดียวกับ CLOTHOID/BLOSS/SINE) ไม่ต้องมีสูตรแยกสำหรับ SPOUT
  ยังไม่แก้โค้ดใดๆ ในรอบนี้ — กลับเข้า plan mode ต่อทันทีหลัง commit
- คำสั่ง: Write .git\smt_commit_msg.txt → git add session_logs/investigate_sinehalfwave_formula.md
  → git commit -F .git\smt_commit_msg.txt
- ผล: PASS — ไม่มี test เกี่ยวข้อง (ไม่แตะโค้ด)
- commit: db1a024

## [2026-07-04] ตรวจสอบสูตร Sine Half-Wavelength (COSINE) spiral — รายงานเท่านั้น

- ทำ: เขียนไฟล์ `session_logs/investigate_sinehalfwave_formula.md` สรุปผลตรวจสอบสูตร
  transition COSINE เทียบเอกสาร Autodesk Civil 3D 2026 Help และคำนวณมือเทียบ ground truth
  2 จุด (R=900/L=100 จาก smt-test1.xml, R=250/L=50 จาก SMT_TEST_ALINGMENT2.xml)
  สรุป: BLOSS/SINE ตรง Autodesk 100% อยู่แล้ว ส่วน COSINE ใช้คนละกลไก (tangent-projected
  distance ไม่ใช่ arc length) มีสูตรปิดที่ยืนยันแล้ว แต่จุดกลางโค้งยังไม่มีข้อมูลยืนยัน
  ยังไม่ได้แก้โค้ดใดๆ ในรอบนี้ — เป็นงานตรวจสอบ/รายงานล้วน
- คำสั่ง: Write session_logs/investigate_sinehalfwave_formula.md → Write .git\smt_commit_msg.txt
  → git add session_logs/investigate_sinehalfwave_formula.md → git commit -F .git\smt_commit_msg.txt
- ผล: PASS — ไม่มี test เกี่ยวข้อง (ไม่แตะโค้ด)
- commit: 6644305

## [2026-07-03] ขยาย .gitignore pattern build_out/ → build_out*/

- ทำ: แก้ `.gitignore` บรรทัด `test_data/build_out/` → `test_data/build_out*/`
  เพื่อ ignore ทุกโฟลเดอร์ output ที่ขึ้นต้นด้วย build_out ไม่ใช่แค่ชื่อเดียว
- คำสั่ง: Edit tool → `git status` (ยืนยัน `test_data/build_out_compound/` หายจาก
  Untracked files แล้ว) → Write `.git\smt_commit_msg.txt` → `git add .gitignore` →
  `git commit -F .git\smt_commit_msg.txt`
- ผล: PASS — `git status` ยืนยัน pattern ใหม่ทำงานถูกต้อง ไม่มี test เกี่ยวข้อง (ไฟล์ config)
- commit: f2e57bb

## [2026-07-03] แก้เอกสาร CLAUDE.md — บันทึกบั๊ก R-drop, ground truth files, roadmap

- ทำ: แก้ `CLAUDE.md` 6 จุดตามที่อาจารย์สั่ง (งานแก้เอกสารเท่านั้น ไม่แตะโค้ด)
  1. เพิ่มรายการใน Known limits: `_flush_pending` ทิ้งค่า R แถว PI เงียบๆ เมื่อมี compound
     sub-row ตามมา (ยังไม่แก้), PI7 ใน SettingOutTest.csv ได้รับผลกระทบห้ามใช้อ้างอิง,
     transition COSINE ผิดจาก Civil 3D ~3cm ที่ R=900 L=100 (CLOTHOID/BLOSS/SINE ยืนยันตรงแล้ว)
  2. เพิ่ม section "Civil 3D Interop ground truth references" — smt-test1.xml, AL_compound.xml
     + compound_curve.csv + so_compound_curve.csv (ยืนยันต่ำกว่า 1mm), py-1.xml
  3. เพิ่ม section "Spiral formula verification methodology" — ต้องมี ground truth ≥2 ชุด
     ต่อ 1 shape ก่อนสรุปว่าสูตรถูกต้อง
  4. เพิ่มกฎใน 4.3 VBA เฉพาะ — แก้ `_shape_integral` ต้องอัปเดต SMT_Core.bas/SMT_Alignment.bas
     พร้อมกันเสมอ
  5. เพิ่ม section "Roadmap" — multicurve.py solver, R-sign auto-derive (backward compatible),
     แยก curvature.py ออกจาก alignment.py
  6. เพิ่มกฎใน Extension policy — Civil 3D interop นับเป็น oracle อีกชั้น ต้องอ้างอิงไฟล์จริงเสมอ
- คำสั่ง: Edit tool ×4 → แสดงเนื้อหาไฟล์เต็มให้ตรวจ → Write `.git\smt_commit_msg.txt` → `git add CLAUDE.md` → `git commit -F .git\smt_commit_msg.txt`
- ผล: PASS (ไม่มี test เกี่ยวข้อง — งานเอกสารล้วน)
- commit: 8f9c9f4
- หมายเหตุ: commit เฉพาะ CLAUDE.md ไฟล์เดียว ไม่แตะไฟล์อื่นที่ค้างอยู่ (session_logs/latest.md เดิม,
  test_data/SettingOutTest.csv, ไฟล์ใหม่ที่ยัง untracked)

## [2026-07-03 16:17] ทดสอบ compound curve engine ด้วยไฟล์ใหม่ pi_compound_curve.csv

- ทำ: สร้าง `test_data/pi_compound_curve.csv` (PI แถวเดียว, RADIUS ว่าง, compound
  2 arc R=30/R=45 ในแถวว่างที่ตามมา — pattern ที่ผ่าน `test_compound()` จริง) แล้วรัน
  `smt build` เทียบผลกับ ground truth จาก Civil 3D (PC/PCC/EP)
- คำสั่ง: `smt build test_data/pi_compound_curve.csv --out-dir test_data/build_out_compound`
- ผล: PASS
  - รอบแรก (Delta arc R=30 ว่างเปล่าตามที่ระบุ) → **crash ทันที** `KeyError: 'delta'`
    ที่ `alignment_builder.py:77` เพราะ arc ที่ไม่ใช่ตัวสุดท้ายต้องมี Delta เสมอ (พิสูจน์แล้วว่า
    เป็นปัญหา input CSV ไม่ใช่บั๊กคำนวณ — โค้ดยังรันไม่ถึงขั้นคำนวณจริง)
  - คำนวณ Delta arc แรกจาก ground truth เอง (อิสระจากโค้ด SMT) ได้ 102.507634° (สอดคล้องกับ
    ระยะ arc length เทียบ station diff ต่างกัน < 1mm) → เติมลง CSV แล้วรันใหม่ → build สำเร็จ
    ไม่มี `warning:` ปรากฏบน stderr เลย (issues list ว่าง)
  - Element ที่ได้ 4 แถว: T (BP→PC) → C R=30 (PC→PCC) → C R=45 (PCC→PT) → T เล็กมาก
    (PT→EP ยาว 0.000831m, เป็น rounding closure ไม่ใช่เส้นตรงจริงคั่นระหว่างโค้ง) — สองโค้งต่อกัน
    ตรงตามคาด ไม่มีเส้นตรงคั่น
  - เทียบ ground truth: PC Δsta=0.7mm ΔN=0.2mm ΔE=0.24mm | PCC (จุดต่อ R=30→R=45)
    Δsta=0.572mm ΔN=0.522mm ΔE=0.288mm | EP Δsta=0.58mm ΔN=ΔE=0mm — ทุกจุดต่างกัน
    ต่ำกว่า 1mm ทั้งหมด → **compound curve engine คำนวณถูกต้อง**
- commit: (ไม่มี — ยังไม่ commit ไฟล์ CSV ใหม่ รอผู้ใช้สั่ง)
- หมายเหตุ: ปัญหาเดิมที่เจอใน SettingOutTest.csv/PI7 (ข้อมูล arc แรกหายเงียบ) คือปัญหา input
  format ไม่ใช่บั๊ก engine — ยืนยันด้วยผลทดสอบนี้

## [2026-07-02] Audit: git diff test_data/build_out/*.csv + เตรียม smoke test 5 tabs

- ทำ: (งานอ่าน/ตรวจสอบเท่านั้น ไม่แก้ core code)
  - รัน `git diff` บน `test_data/build_out/controls_so_output.csv` และ `elements_output.csv`
    ที่ค้าง modified มาตั้งแต่ก่อน session นี้ → พบว่าค่าตัวเลขไม่เปลี่ยน เปลี่ยนแค่ precision
    (3dp→6dp) กับ Transition column (T/C แถวเคยมี CLOTHOID ติดผิดๆ ตอนนี้ว่างถูกต้อง)
  - สืบ git log เจอสาเหตุ: commit `dad90fb` (smt build: 6-decimal output, fix Transition
    column) แก้ format ใน cli.py แต่ไฟล์ output ใน test_data/build_out/ ถูก commit ครั้งล่าสุดที่
    `3b0afff` ซึ่งเกิดก่อนหน้านั้น — ไฟล์เลย stale ไม่ใช่บั๊ก สรุปว่าปลอดภัย restore ทิ้งได้
    (ยังไม่ restore/commit ให้ รอผู้ใช้ตัดสินใจ)
  - พบเพิ่ม: `.gitignore` มี `test_data/build_out/` อยู่แล้วแต่สองไฟล์นี้ยัง track ค้างจากก่อนกฎ ignore
  - ตรวจ header ไฟล์ทดสอบใน test_data/ ที่จะใช้ smoke test — พบว่าไฟล์ที่ผู้ใช้ระบุไว้สำหรับ
    Cross-Check tab (`r01n01_so_crosscheck.csv`) เป็น drawing-point format (Name,STA,N,E)
    ไม่ใช่ field-survey format (NAME,N,E,Z,DISC) ที่ tab ต้องการ → แก้เป็น `Bulk_cross-check.csv`
    แทน; ไฟล์ drawing point ที่ตรง alignment เดียวกับ SettingOutTest.csv คือ
    `test_data/build_out/controls_so_output.csv` (ไม่ใช่ r01n01_so_crosscheck.csv ซึ่งเป็นคนละ
    alignment/ramp01n01)
  - สร้าง `~/.streamlit/credentials.toml` (email="") เพื่อข้าม onboarding prompt ที่ทำให้
    `streamlit run app.py` แบบไม่ headless ค้างรอ stdin ตอนรันครั้งแรกบนเครื่องนี้
  - เปิด `streamlit run app.py --server.port=8501` (ไม่ headless ตามที่ขอ) ทิ้งไว้ให้เปิดเบราว์เซอร์ทดสอบเอง
- คำสั่ง: `git diff`, `git log --oneline -p -- src/smt/cli.py`, `git log -S"transition_val"`,
  `git ls-files test_data/build_out/`, `streamlit run app.py --server.port=8501` (background)
- ผล: PASS — server ตอบ HTTP 200, ไม่มี error ใน log
- commit: ไม่มี (งานอ่าน/ตรวจสอบ + เปิด dev server เท่านั้น)
- หมายเหตุ: ระหว่างทำงานพลาดเผลอ Write ทับ `session_logs/latest.md` ด้วย placeholder ชั่วขณะหนึ่ง
  — กู้คืนด้วย `git restore` ทันที ไม่มีข้อมูลสูญหาย

## [2026-07-02] Streamlit web UI (app.py) — 5 tabs, revision 2 ของแผน

- ทำ: implement ตามแผนที่อนุมัติแล้ว (`session_logs/plan_streamlit_ui_20260701_1400.md`, revision 2):
  - สร้าง `src/smt/webhelpers.py` — 4 pure helper functions (`read_csv_rows`,
    `parse_field_points`, `parse_drawing_points`, `parse_element_rows`) ไม่ import
    streamlit เลย, mirror `cli.py`'s private helpers ตรงๆ (รวมถึง `disc` default = `''`
    ไม่ใช่ `0.0` ตามจุดที่แก้ในแผน)
  - สร้าง `app.py` (root) — Streamlit UI 5 tabs (Build, Cross-Check, Compare Drawing,
    Fit Radius, Export LandXML) import helper จาก `smt.webhelpers`
  - Fit Radius verification table + Compare Drawing table มี column `status` แยก
    (`OK`/`OUTSIDE_ALIGNMENT`/`HIP`) ไม่ปนกับตัวเลขใน `calc_N/calc_E/gap_m` แล้ว
  - เพิ่ม `tests/test_app_helpers.py` (8 tests) import ตรงจาก `smt.webhelpers`
  - แก้ `pyproject.toml` — เพิ่ม `[project.optional-dependencies] ui = ["streamlit>=1.30", "pandas>=1.5"]`
    (เพิ่ม pandas เพราะ `app.py` ใช้ `DataFrame.to_csv()` ตามที่แผนระบุไว้ — streamlit เองก็ต้องพึ่ง pandas อยู่แล้ว)
- คำสั่ง: `pytest tests/test_app_helpers.py -q` → `pytest -q` → smoke test จริงด้วย
  `streamlit run app.py --server.headless=true --server.port=8765` + `curl localhost:8765`
  → ทดสอบ `webhelpers.parse_element_rows` กับไฟล์จริง `test_data/build_out/elements_output.csv`
- ผล: PASS — helper tests 8/8, full suite 452/452, smoke test HTTP 200 ไม่มี error ใน log,
  ไฟล์จริง parse ได้ 31 elements ถูกต้อง
- commit: df7d8fd
- หมายเหตุ: ยังไม่ push — รอคำสั่งผู้ใช้

## [2026-07-01] สลับ mapping SINE/COSINE ใน _spiral_lx_type

- ทำ: แก้ `src/smt/landxml.py` — `_SPIRAL_TYPE`: SINE→sinusoid (เดิม sineHalfWave), COSINE→sineHalfWave
  (เดิม sinusoid) CLOTHOID→clothoid และ BLOSS→bloss เหมือนเดิม
  - เพิ่ม test ใหม่ `test_spiral_lx_type_mapping` ใน `tests/test_landxml.py` ตรวจ mapping ทั้ง 4 ตัวตรงๆ
    (ของเดิมไม่มี test คุม SINE/COSINE โดยตรง)
- คำสั่ง: `pytest -q` → `smt export-landxml test_data/SettingOutTest.csv --name SettingOutTest --out test_data/SettingOutTest.xml`
- ผล: PASS 444/444 — smoke test: ตรวจ SettingOutTest.xml พบ PI4 (COSINE) → spiType="sineHalfWave",
  PI5 (SINE) → spiType="sinusoid" ตรงกับ mapping ใหม่
- commit: 5e98645

---

## [2026-07-01] เปลี่ยนวิธีคำนวณ totalX/totalY/tanLong/tanShort เป็นแบบ canonical (ไม่ขึ้นกับทิศทางจริง)

- ทำ: แก้ `src/smt/landxml.py`
  - ลบวิธีคำนวณเดิมที่ใช้พิกัด start/end จริง (`_spiral_geometry` แบบเดิมที่หมุนพิกัดจริงเข้า local frame) ทิ้งทั้งหมด
  - เขียน `_spiral_geometry(R, length, transition, theta_rad)` ใหม่: สร้าง synthetic `Element`
    ที่ n=0, e=0, azimuth=0, sta_start=0, sta_end=length, k_in=0, k_out=1/R (R คือรัศมีจำกัดเสมอ
    ไม่ว่า SPIN หรือ SPOUT), transition เดียวกับของจริง แล้วเรียก `calculate_point_on_element`
    ที่ distance=length ได้ local_n, local_e → totalX=local_n, totalY=local_e (บวกทั้งคู่)
    theta_rad ใช้ค่าเดียวกับที่คำนวณไว้แล้วสำหรับ attribute theta
    tanLong = totalX - totalY/tan(theta_rad), tanShort = totalY/sin(theta_rad)
  - import `calculate_point_on_element` เพิ่มจาก `.alignment`
  - Curve element ไม่แตะเลย
  - อัปเดต docstring
  - แก้ `tests/test_landxml.py`: `test_spout_geometry_attributes` เดิม (เทียบค่าจาก SPOUT พิกัดจริง)
    ใช้ไม่ได้แล้วเพราะตอนนี้ SPIN/SPOUT ที่ R และ length เท่ากันต้องได้ค่าเดียวกัน (canonical)
    → แทนที่ด้วย `test_spout_geometry_matches_spin` (เทียบ SPIN==SPOUT) และเพิ่ม
    `test_geometry_attributes_are_positive` (ตรวจ totalX, totalY > 0 ทุก Spiral)
- คำสั่ง: `pytest -q` → `smt export-landxml test_data/SettingOutTest.csv --name SettingOutTest --out test_data/SettingOutTest.xml`
- ผล: PASS 443/443 — smoke test: ตรวจ SettingOutTest.xml พบ SPIN/SPOUT คู่เดียวกัน (R, length เท่ากัน)
  ได้ totalX/totalY/tanLong/tanShort เท่ากันทุกคู่ ค่าทั้งหมดเป็นบวก, Curve ไม่เปลี่ยนแปลง
- commit: 3715369

---

## [2026-07-01] เพิ่ม totalX/totalY/tanLong/tanShort ใน Spiral element ทุกตัว

- ทำ: แก้ `src/smt/landxml.py`
  - เพิ่ม helper `_spiral_geometry(start_n, start_e, end_n, end_e, entry_azimuth_rad, theta_rad)`
    คำนวณ dN/dE → totalX, totalY (หมุนเข้า local frame ตาม entry azimuth) → tanLong, tanShort
    ตามสูตรที่กำหนด (tanLong = totalX - totalY/tan(theta), tanShort = totalY/sin(theta))
  - refactor `_theta_deg` → `_theta_rad` (คืนค่า radian แทน แล้วแปลงเป็นองศาตอนใส่ attribute theta)
    เพื่อให้ theta_rad ใช้ร่วมกับ _spiral_geometry ได้โดยไม่คำนวณซ้ำ
  - เพิ่ม attributes `totalX`, `totalY`, `tanLong`, `tanShort` (เมตร, ทศนิยม 6 ตำแหน่ง) ในทุก Spiral
    (SPIN และ SPOUT) รักษา rot, radiusStart, radiusEnd, spiType, length, theta ไว้เหมือนเดิม
  - Curve element ไม่แตะเลย
  - อัปเดต docstring
  - เพิ่ม test ใหม่ใน `tests/test_landxml.py`: `test_spin_geometry_attributes`, `test_spout_geometry_attributes`
    (ตรวจค่าตัวเลขจริงจาก fixture spiral symmetric R=400 Ls=60)
- คำสั่ง: `pytest -q` → `smt export-landxml test_data/SettingOutTest.csv --name SettingOutTest --out test_data/SettingOutTest.xml`
- ผล: PASS 442/442 — smoke test: ตรวจ SettingOutTest.xml พบ Spiral ทุกตัวมี totalX/totalY/tanLong/tanShort ครบ, Curve ยังคงเดิมไม่เปลี่ยนแปลง
- commit: acb56cd

---

## [2026-07-01] ลบ dirStart/dirEnd ออกจาก Spiral, เพิ่ม theta แทน (Curve ไม่แตะ)

- ทำ: แก้ `src/smt/landxml.py` ส่วนสร้าง Spiral (SPIN และ SPOUT)
  - ลบ `dirStart`/`dirEnd` ออกทั้งหมดจาก Spiral (Civil 3D ไม่ใช้ attribute นี้กับ Spiral)
  - เพิ่ม attribute `theta` = มุมเลี้ยวรวมของ spiral (องศา, ค่าสัมบูรณ์) คำนวณจาก
    `theta_deg = abs(rad_to_deg(calculate_angle_diff(exit_azimuth, entry_azimuth)))`
    โดยเพิ่ม helper `_theta_deg` ใหม่
  - Curve ยังคงมี `dirStart`/`dirEnd` เหมือนเดิม ไม่แตะ
  - attribute อื่นของ Spiral (rot, radiusStart, radiusEnd, spiType, length) คงเดิม
  - อัปเดต docstring
  - แก้ `tests/test_landxml.py`: เอา `test_spin_dir_start`/`test_spin_dir_end` ออก แทนที่ด้วย
    `test_spiral_no_dir_start`, `test_spiral_no_dir_end`, `test_spin_theta`, `test_spout_theta`
    (คาดค่า theta ≈ 4.297183° จาก 0.5 * k_out * L)
- คำสั่ง: `pytest -q` → `smt export-landxml test_data/SettingOutTest.csv --name SettingOutTest --out test_data/SettingOutTest.xml`
- ผล: PASS 440/440 — smoke test: ตรวจ SettingOutTest.xml พบ Spiral มี theta ทุกตัว ไม่มี dirStart/dirEnd หลงเหลือ, Curve ยังมี dirStart/dirEnd ครบ
- commit: 47e38b9

---

## [2026-07-01] ลบ attribute "type" ออกจาก Spiral, ใช้ "spiType" ใส่รูปร่าง spiral แทน toCurve/fromCurve

- ทำ: แก้ `src/smt/landxml.py` ส่วนสร้าง Spiral (SPIN และ SPOUT)
  - ลบ attribute `type=_spiral_lx_type(...)` ออกทั้งหมด
  - เปลี่ยน `spiType='toCurve'`/`spiType='fromCurve'` → `spiType=_spiral_lx_type(el.transition)` (ใส่ค่ารูปร่าง clothoid/bloss/sinusoid/sineHalfWave แทน)
  - attribute อื่น (rot, radiusStart, radiusEnd, length, dirStart, dirEnd) คงเดิมทั้งหมด
  - อ้างอิงจาก py-1.xml (Civil 3D 2023 export จริง) ที่ Spiral มีแค่ length, radiusEnd, radiusStart, rot, spiType — ไม่มี type, ไม่มี toCurve/fromCurve
  - อัปเดต docstring ให้ตรงกับ format ใหม่
  - แก้ `tests/test_landxml.py`: เปลี่ยนตัวเลือก spin/spout จาก `spiType=='toCurve'` เป็น `radiusStart=='INF'`; ลบ `test_spin_spi_type`/`test_spout_spi_type`/`test_spiral_type_clothoid` แทนที่ด้วย `test_no_type_attribute`, `test_spi_type_holds_shape`, `test_no_to_from_curve_values`
- คำสั่ง: `pytest -q` → `smt export-landxml test_data/SettingOutTest.csv --name SettingOutTest --out test_data/SettingOutTest.xml`
- ผล: PASS 438/438 — smoke test: ตรวจ SettingOutTest.xml พบ Spiral มี spiType="clothoid"/"bloss"/"sinusoid" ไม่มี type attribute ไม่มี toCurve/fromCurve เหลืออยู่เลย
- commit: 37b4bdf

---

## [2026-07-01] แก้ _rotation ให้คืน "cw"/"ccw" แทน "right"/"left"

- ทำ: แก้ `src/smt/landxml.py` ฟังก์ชัน `_rotation` — คืน `"cw"` เมื่อ k>0, `"ccw"` เมื่อ k<0
  (อ้างอิงจากไฟล์ py-1.xml ที่ Civil 3D 2023 export จริง ใช้ rot="cw"/"ccw" เท่านั้น ไม่เคยใช้ "right"/"left")
  - อัปเดต module docstring และ function docstring ให้ตรงกับค่าใหม่
  - แก้ `tests/test_landxml.py`: `test_rotation_right` → `test_rotation_cw` (assert `'cw'`), `test_left_turn_rotation` assert `'ccw'` แทน `'left'`
- คำสั่ง: `pytest -q` → `smt export-landxml test_data/SettingOutTest.csv --name SettingOutTest --out test_data/SettingOutTest.xml` → `smt export-landxml test_data/ramp01n01_SO.csv --name ramp_test --out test_data/mainline_test.xml`
- ผล: PASS 438/438 — smoke test: ทั้งสองไฟล์ export สำเร็จ, ตรวจ mainline_test.xml พบ rot="cw"/"ccw" เท่านั้น ไม่มี "right"/"left" หลงเหลือ
- commit: d743e31

---

## [2026-07-01] แก้ spiral type mapping + dirStart/dirEnd Civil 3D convention + คืน dirEnd

- ทำ: แก้ `src/smt/landxml.py` 3 จุดตามแผนที่อนุมัติ
  1. `_spiral_lx_type`: CLOTHOID→clothoid, BLOSS→bloss, SINE→sineHalfWave, COSINE→sinusoid (ตรงกับ Civil 3D จริง แทนที่จะ map ทุกอย่างเป็น clothoid)
  2. เพิ่ม `_to_civil_dir(az_rad)` แปลง SMT survey azimuth (radian, 0=North clockwise) → Civil 3D dir (decimal degrees, 0=East counterclockwise) ด้วย `(450 - deg) mod 360`; ใช้แทน `rad_to_deg` ตรงๆ ทุกจุดที่เขียน dirStart
  3. เพิ่ม `dirEnd` กลับเข้า Curve/Spiral ทุกตัว โดยใช้ `_to_civil_dir` กับ exit azimuth (เพิ่ม helper `_exit_azimuth`)
  - `_rotation` ตรวจแล้วคืน "right"/"left" (ไม่ใช่ "cw"/"ccw") — ของเดิมถูกอยู่แล้วตาม test ที่ผ่าน จึงไม่แก้
  - อัปเดต `tests/test_landxml.py`: `test_curve_dir_start` (คาด 0.0 แทน 90.0 ตาม civil convention), เพิ่ม `test_curve_dir_end` (คาด 270.0), `test_spin_dir_start` (คาด 0.0), เพิ่ม `test_spin_dir_end` (คาดว่า dirEnd ไม่ใช่ None)
- คำสั่ง: `pytest -q` → `smt export-landxml test_data/SettingOutTest.csv --name SettingOutTest --out test_data/SettingOutTest.xml` → `smt export-landxml test_data/ramp01n01_SO.csv --name ramp_test --out test_data/mainline_test.xml`
- ผล: PASS 438/438 — smoke test: ทั้งสองไฟล์ export สำเร็จ, ตรวจ XML พบ dirStart/dirEnd ต่อเนื่องกันระหว่าง element ถัดไป และ spiral type ตรงกับ BLOSS/COSINE/SINE ที่ใช้จริงใน ramp01n01_SO.csv
- commit: 4bc4f09

---

## [2026-07-01] ลบ dirEnd ออกจาก Curve และ Spiral ใน LandXML export

- ทำ: ลบ `dirEnd` attribute ออกจาก Curve, SPIN, SPOUT ทุกตัวใน `src/smt/landxml.py`
  - ลบ `_exit_azimuth_deg` helper (กลายเป็น dead code)
  - อัปเดต module docstring และ function docstring
  - แก้ `tests/test_landxml.py`: เปลี่ยน `test_curve_dir_end` → `test_curve_no_dir_end` (assert `dirEnd is None`) และ `test_spin_dir_end_is_float` → `test_spin_no_dir_end`
- คำสั่ง: `pytest -q` → `smt export-landxml test_data/SettingOutTest.csv --name SettingOutTest --out test_data/SettingOutTest.xml`
- ผล: PASS 438/438 — smoke test: XML regenerated ปกติ
- commit: 1280fb0

---

## [2026-07-01] Map BLOSS/COSINE/SINE spiral types to clothoid in LandXML export

- ทำ: แก้ `_SPIRAL_TYPE` dict ใน `src/smt/landxml.py` — ลบ BLOSS/COSINE/SINE ออก (ทั้ง 3 ตัว fall through เป็น 'clothoid' via default ใน `.get(..., 'clothoid')` อยู่แล้ว)
- คำสั่ง: `pytest -q` → `smt export-landxml test_data/SettingOutTest.csv --name SettingOutTest --out test_data/SettingOutTest.xml`
- ผล: PASS 438/438 (ไม่มี regression) — smoke test: XML regenerated ปกติ
- commit: abc2e7c

---

## [2026-06-30] LandXML 1.2 export — landxml.py + CLI + 27 tests

- ทำ: สร้าง LandXML 1.2 export feature ครบ 3 ไฟล์
  - `src/smt/landxml.py`: pure function `export_alignment_landxml(build_result, name)` — T→`<Line>`, C→`<Curve>` + Center, SPIN→`<Spiral radiusStart="INF">`, SPOUT→`<Spiral radiusEnd="INF">`, rot="right"/"left" (Civil 3D 2023), transition types mapped ครบ (clothoid/bloss/cosineCurve/sineCurve)
  - `src/smt/cli.py`: เพิ่ม subcommand `smt export-landxml <pi.csv> [--name] [--out]`
  - `tests/test_landxml.py`: 27 tests — TestTangentOnly (7), TestSimpleCurve (7), TestSpiralIn (8), TestAnglePoint (5)
- คำสั่ง: `pytest tests/test_landxml.py -v`, `pytest -q`, `smt export-landxml test_data/SettingOutTest.csv --name SettingOutTest`
- ผล: PASS 27/27 (landxml), PASS 434/434 (full suite, ไม่มี regression)
- smoke test: XML ถูกต้องครบทุก element type รวม BLOSS/COSINE/SINE spirals และ angle points
- commit: f1f07d1

## [2026-06-30] เปลี่ยนชื่อ function ใน SMT_Geometry.bas + อัปเดต README

- ทำ: เปลี่ยนชื่อ 2 functions ใน `reference/vba/SMT_Geometry.bas` (ทุกที่: declaration, comment, expected values)
  - `SMT_GlobalToChn` → `SMT_GlobalToY`
  - `SMT_GlobalToOfs` → `SMT_GlobalToX`
- อัปเดต `reference/vba/README.md`: ชื่อ function ในตาราง reference และ example usage
- คำสั่ง: Edit tool replace_all=true × 4 → git commit -F
- ผล: commit รวมกับ notebooks/02_alignment_fitting.ipynb + alignment_fitting.png

## [2026-06-30] สร้าง notebooks/02_alignment_fitting.ipynb — alignment fitting visualisation

- ทำ: สร้าง Jupyter notebook 5 sections ใช้ข้อมูลจริง `test_data/ramp01n01_SO.csv` + `test_data/r01n01_so_crosscheck.csv`
  - Section 1 Setup: load PI CSV (pi_rows ไว้ส่ง optimizer), build alignment เริ่มต้น, load drawing points → active_pts (non-PI/HIP)
    Summary: 12 elements, 13 control pts, 15 drawing pts / 9 active
  - Section 2 Before Plot: helper functions (_compute_gaps, _trace_centreline, _plot_alignment)
    centreline สีน้ำเงิน, control pts สีน้ำเงิน, drawing pts X สีแดง, gap vectors ×100 สีแดง
  - Section 3 Optimizer: fit_radius(pi_rows, drawing_points) → 5 free PIs, 289 iters, converged
    gap_before → gap_after ลดลง
  - Section 4 After Plot: patch pi_rows ด้วย r_optimized → rebuild → plot เหมือน Section 2
    export PNG → notebooks/alignment_fitting.png (dpi=150)
  - Section 5 Table: pandas DataFrame Name/STA/gap_before/gap_after/improvement% พร้อม green bar
- tools: gen_notebook.py (nbformat) → nbconvert --execute --inplace → verified all cells pass, no errors
- คำสั่ง: python gen_notebook.py → jupyter nbconvert --execute → git add → git commit -F
- ผล: commit 215bc82 — 2 files, 588 insertions (02_alignment_fitting.ipynb + alignment_fitting.png)

## [2026-06-30] จัดโครงสร้าง reference/vba/ ใหม่ — 7 modules → 5 modules

- ทำ: รวมไฟล์ VBA ใน `reference/vba/` จาก 7 ไฟล์เป็น 5 ไฟล์
  - `SMT_Core.bas` ใหม่: รวม SMT_FPMath + SMT_WCB (FPMath ก่อน, WCB ตาม)
  - `SMT_Alignment.bas` ใหม่: เปลี่ยนชื่อจาก SMT_Align + ดูด SMT_WCBatSta มาจาก SMT_Rotation3D
  - `SMT_Geometry.bas` ใหม่: รวม SMT_LocalCoord + RotX/RotY/RotZ จาก SMT_Rotation3D
  - `SMT_Vertical.bas`, `SMT_Crossfall.bas` คงเดิม ไม่เปลี่ยน
  - ลบ: SMT_FPMath.bas, SMT_WCB.bas, SMT_Align.bas, SMT_LocalCoord.bas, SMT_Rotation3D.bas
  - อัปเดต Attribute VB_Name ทุกไฟล์ใหม่
  - เขียน README.md ใหม่ทั้งหมด: dependency diagram (ASCII) + function reference ครบ 5 modules
- คำสั่ง: Write tool (SMT_Core/Alignment/Geometry.bas + README) → Remove-Item → git add -u → git commit -F
- ผล: commit 8a15ee7 — 6 files changed, 379 insertions, 399 deletions
- โครงสร้างใหม่: SMT_Core → SMT_Alignment (dep Core), SMT_Vertical, SMT_Crossfall, SMT_Geometry (dep Core)

## [2026-06-30] สร้าง SMT_Rotation3D.bas — 3-D rotation + WCB at station

- ทำ: สร้าง `reference/vba/SMT_Rotation3D.bas` — 2 ส่วน
- ส่วน 1: SMT_RotX, SMT_RotY, SMT_RotZ (port จาก code อาจารย์, แก้ 4 จุด)
  - Fix1: Dim i As Long (เดิม Integer ล้น >32767)
  - Fix2: nRows As Long
  - Fix3: คืน array ใหม่ (เดิม ByRef แก้ต้นฉบับ)
  - Fix4: cosA/sinA คำนวณครั้งเดียวก่อน loop
  - Convention: right-hand rule CCW, angle in radians, pts 1-based n×3 Variant
- ส่วน 2: SMT_WCBatSta(sta, rng) — tangent WCB (degrees,[0,360)) ที่ station ใดๆ
  - T: theta=0 | C: theta=d/R | SPIN: d²/(2RL) | SPOUT: d/R-d²/(2RL)
  - คืน degrees เพื่อใช้กับ SMT_LocalToN/E ได้ทันที
- อัปเดต `reference/vba/README.md` เพิ่ม SMT_Rotation3D reference tables
- คำสั่ง: Write tool → git add → git commit -F
- ผล: commit fd36af5 — 2 files changed, 246 insertions
- Expected values:
  RotZ([1,0,0], pi/2) = [0,1,0] | SMT_WCBatSta(0, SMT_Elements) = 90.0

## [2026-06-30] สร้าง SMT_LocalCoord.bas — Local ↔ Global coordinate conversion

- ทำ: สร้าง `reference/vba/SMT_LocalCoord.bas` port และปรับปรุงจาก CHOStoNE/NEtoCHOS
  - `SMT_LocalToN(n0,e0,aziBEG,chn,ofs)` — Local→Northing
  - `SMT_LocalToE(n0,e0,aziBEG,chn,ofs)` — Local→Easting
  - `SMT_GlobalToChn(n0,e0,aziBEG,n,e)` — Global→Chainage
  - `SMT_GlobalToOfs(n0,e0,aziBEG,n,e)` — Global→Offset (+right/-left)
- Forward: DS=Sqr(chn²+ofs²); localAz=SMT_Atan2(ofs,chn); globalAz=NormalizeAngle(localAz+aziBEG_rad); N=n0+DS*Cos, E=e0+DS*Sin
- Inverse: Chn=dN*Cos(az)+dE*Sin(az); Ofs=-dN*Sin(az)+dE*Cos(az)
- Private SMT_Atan2 ซ้ำมาจาก SMT_WCB (VBA ไม่อนุญาต cross-module Private access)
- aziBEG รับเป็น degrees แปลง radians ทันทีใน entry point
- อัปเดต `reference/vba/README.md` เพิ่ม SMT_LocalCoord reference table
- คำสั่ง: Write tool (SMT_LocalCoord.bas + README) → git add → git commit -F
- ผล: commit e6ba7eb — 2 files changed, 213 insertions
- Expected values ท้ายไฟล์ (Origin=1000,2000 az=90°):
  LocalToN(100,0)=1000.0 | LocalToE(100,0)=2100.0 | LocalToN(0,50)=950.0
  GlobalToChn(1000,2100)=100.0 | GlobalToOfs(950,2000)=50.0

## [2026-06-30] สร้าง SMT_Crossfall.bas — VBA port of crossfall.py (crossfall/superelevation lookup)

- ทำ: สร้าง `reference/vba/SMT_Crossfall.bas` พอร์ต 2 public functions จาก `src/smt/crossfall.py`
  - `SMT_CrossfallLeft(sta, rng)`  — left crossfall (%) ที่ station sta
  - `SMT_CrossfallRight(sta, rng)` — right crossfall (%) ที่ station sta
- Named Range SMT_Crossfall: 6 คอลัมน์ (StaStart, StaEnd, CF_L_Start, CF_L_End, CF_R_Start, CF_R_End)
- Algorithm: linear interpolation ภายใน segment: CF = CF_Start + (CF_End-CF_Start)*(sta-StaStart)/(StaEnd-StaStart)
- Station range rule ตรง Python oracle: [StaStart,StaEnd) ยกเว้น last segment [StaStart,StaEnd]
- Sign: ลบ=ลาดออกจาก centerline (ระบายน้ำปกติ), บวก=ลาดเข้าหา centerline (superelevation)
- อัปเดต `reference/vba/README.md` เพิ่ม SMT_Crossfall reference table
- คำสั่ง: Write tool (SMT_Crossfall.bas + README) → git add → git commit -F
- ผล: commit c022258 — 2 files changed, 156 insertions
- Expected values (project dataset):
  sta=0→-2.0 | sta=530 Left→-1.0 (runout mid) | sta=700 Left→7.0 (full super) | sta=530 Right→-2.0

## [2026-06-30] สร้าง SMT_Vertical.bas — VBA port of vertical.py (elevation lookup)

- ทำ: สร้าง `reference/vba/SMT_Vertical.bas` พอร์ต 1 public function จาก `src/smt/vertical.py`
  - `SMT_Elevation(sta, rng)` — คำนวณ elevation ที่ station ใดๆ จาก Named Range SMT_Vertical (7 คอลัมน์)
- รองรับ 3 ประเภท segment:
  - LVC=0 → tangent grade: `Level + G1/100 * lx`
  - LVC>0, LVC2=0 → symmetric VC: `base + (G2-G1)/(200*LVC) * lx^2`
  - LVC>0, LVC2>0 → asymmetric VC: middle ordinate `e = L1*L2/(200*(L1+L2))*(G2-G1)`, arm1/arm2 formula
- Station range rule ตรง Python oracle: interior [StaStart,StaEnd), last [StaStart,StaEnd]
- อัปเดต `reference/vba/README.md` เพิ่ม SMT_Vertical reference table
- คำสั่ง: Write tool (SMT_Vertical.bas + README) → git add → git commit -F
- ผล: commit e77f438 — 2 files changed, 224 insertions
- Expected values (golden dataset):
  sta=0→100.0 | sta=1200→117.34375 | sta=2750→100.715075 | sta=2900→100.858475

## [2026-06-30] สร้าง SMT_Align.bas — VBA port of alignment.py (forward + inverse)

- ทำ: สร้าง `reference/vba/SMT_Align.bas` พอร์ต 4 public functions จาก `src/smt/alignment.py`
  - `SMT_StaToN(sta, offset, rng)` — Forward: sta+offset → Northing
  - `SMT_StaToE(sta, offset, rng)` — Forward: sta+offset → Easting
  - `SMT_CoordToSta(n, e, rng)`    — Inverse: N,E → station
  - `SMT_CoordToOffset(n, e, rng)` — Inverse: N,E → offset (+right/-left)
- Algorithm: Tangent=dot-product/straight-line; Circular=chord-half-angle/centre-of-curvature; Spiral=Simpson 48 steps (ทุก transition shape) + bisection inverse 50 รอบ
- อัปเดต `reference/vba/README.md` เพิ่ม SMT_Align function reference table
- คำสั่ง: Write tool (SMT_Align.bas + README) → git add → git commit -F
- ผล: commit 731bcc1 — 2 files changed, 540 insertions
- Expected values ท้ายไฟล์:
  SMT_StaToN(0,0,SMT_Elements)=1568000.0 | SMT_StaToE(519.615,0,SMT_Elements)=678519.615
  SMT_CoordToSta(1568000,678000,SMT_Elements)=0.0 | SMT_CoordToOffset(...)=0.0

## [2026-06-30] สร้าง SMT_WCB.bas — VBA port of wcb.py

- ทำ: สร้าง `reference/vba/SMT_WCB.bas` (VBA Module) พอร์ต 4 functions จาก `src/smt/wcb.py`
  1. `SMT_Azimuth(n1,e1,n2,e2)` — WCB azimuth rad [0,2π), guard coincident point
  2. `SMT_Distance(n1,e1,n2,e2)` — plan distance via Sqr(dN²+dE²)
  3. `SMT_CalcForward(n,e,az,dist,result)` — forward calc, result="N"/"E"
  4. `SMT_CalcOffset(n,e,az,dist,offset,result)` — forward + perpendicular offset
  - Private helper `SMT_Atan2(y,x)`: atan2 ครบ 5 quadrant cases (VBA ไม่มี built-in atan2)
  - Dependency: SMT_FPMath — เรียก `SMT_Pi()` และ `SMT_NormalizeAngle()` อย่าคำนวณซ้ำ
  - Expected values ท้ายไฟล์ตรงกับ Python golden data ทุกกรณี
- คำสั่ง: Write tool (ไม่มี test รัน — VBA module ต้องทดสอบใน Excel)
- ผล: ไฟล์สร้างสำเร็จ — ยังไม่ได้ commit

---

## [2026-06-30] สร้าง SMT_FPMath.bas — VBA port of fpmath.py

- ทำ: สร้าง `reference/vba/SMT_FPMath.bas` (VBA Module) พอร์ต 5 functions จาก `src/smt/fpmath.py`
  1. `SMT_Pi()` — คืนค่า π ด้วย `4 * Atn(1)` เต็ม Double precision
  2. `SMT_DegToRad(deg)` — degrees → radians
  3. `SMT_RadToDeg(rad)` — radians → degrees
  4. `SMT_NormalizeAngle(az)` — normalize rad ให้อยู่ใน [0, 2π)
  5. `SMT_AngleDiff(a, b)` — signed shortest diff (a-b) ใน (-π, π]
  - Private helper `SMT_FloorMod` ใช้ `Int()` แทน VBA `Mod` (ซึ่งแปลงเป็น Long ก่อน ทำให้ Double ผิด)
  - ท้ายไฟล์: expected values เทียบ Python golden data ครบ 8 กรณี
  - อัปเดต `reference/vba/README.md`: วิธี import .bas เข้า Excel, column mapping SMT_Elements, sign convention
- คำสั่ง: Write tool (ไม่มี test รัน — VBA module ต้องทดสอบใน Excel)
- ผล: ไฟล์สร้างสำเร็จ — ยังไม่ได้ commit
- หมายเหตุ: VBA Mod operator ทำงานกับ Integer/Long เท่านั้น ต้องใช้ `a - Int(a/n)*n` สำหรับ Double floor-mod

---

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

## [2026-07-27 15:40] สร้างไฟล์ continuity ข้ามแชท 4 ไฟล์ (PROJECT_STATE, BUNDLE_gsheet, BUNDLE_python_core, DEPENDENCY_MAP)

- ทำ: ตรวจร่าง PROJECT_STATE.md ที่ผู้ใช้เตรียมไว้ (พบที่ root แล้ว, timestamp
  ตรงกับ session นี้) เทียบกับสภาพจริงในเครื่อง 2 จุดตามที่ผู้ใช้ขอ:
  - §3 รายชื่อไฟล์ .gs + dependency: grep `require\(` จริงใน reference/*.gs +
    reference/gsheet/*.gs ตรงกับตารางในร่างทุกแถว (FPMath ไม่มี dep, WCB->FPMath,
    GS_Alignment->FPMath+WCB, GS_AlignmentBuilder/GS_CrossCheck->FPMath+WCB+
    GS_Alignment, GS_TableSplitter/GS_PiTableParser ไม่มี dep, GS_ElementTable->
    FPMath) — ไม่พบจุดที่ไม่ตรง
  - §4 ฟังก์ชันใน TestDrive.js: grep `^function` ใน D:\MyClasp_SMT_DEMO\TestDrive.js
    ได้ 10 ฟังก์ชัน ตรงกับลิสต์ในร่างทุกตัว ไม่มีฟังก์ชันเกิน
  ผลตรวจ: ร่างถูกต้อง ไม่ต้องแก้ — บันทึกไว้ที่ root ตามที่ขอ
  สร้างเพิ่มอีก 3 ไฟล์:
  - BUNDLE_gsheet.md: concat FPMath.gs, WCB.gs, GS_Alignment.gs,
    GS_AlignmentBuilder.gs, GS_TableSplitter.gs, GS_PiTableParser.gs,
    GS_ElementTable.gs, GS_CrossCheck.gs (ลำดับที่ผู้ใช้ระบุ ตรวจแล้วว่าเป็น
    dependency order ที่ถูกต้องพอดี)
  - BUNDLE_python_core.md: concat fpmath.py, wcb.py, alignment.py, check.py,
    builders/table_splitter.py, builders/alignment_builder.py, + cli.py
    บรรทัด 109-168 เฉพาะ _radius_from_element/_run_build
  - DEPENDENCY_MAP.md: ตาราง dependency จาก grep จริง + หมายเหตุสำคัญว่า
    require() มีผลแค่ตอนรัน Node local เท่านั้น ไม่มีผลใน Apps Script runtime
    จริง (global scope เดียวกันหมด ไม่มีโฟลเดอร์) — อธิบายรากของปัญหา Session C
- คำสั่ง: grep require\( ข้าม reference/, reference/gsheet/; grep ^function
  TestDrive.js; ls ตรวจ D:\MyClasp_SMT_DEMO\
- ผล: PASS — ไม่มี test รันเพราะเป็นเอกสารล้วนๆ ไม่กระทบโค้ดจริง
- commit: (ยังไม่ commit — รอผู้ใช้ตรวจสรุปตามมาตรฐาน ส่วนที่ 3/6)
- หมายเหตุ: 4 ไฟล์ทั้งหมดเป็นเอกสารอ้างอิง ไม่แก้โค้ดใดๆ ในโปรเจกต์

## [2026-07-28 17:34] Session F.3 — สร้าง cascade UI (Index.html + doGet)

- ทำ: ทำตามแผนที่อนุมัติแล้วใน DRAFT_plan_session_F3_cascade_ui.md ทุกข้อ
  (หัวข้อ 4-7) สร้าง 2 ไฟล์ใหม่:
  - `reference/gsheet/Index.html` — 3 dropdown cascade (หมวด→ไฟล์→alignment)
    แสดงตลอด disabled รอ parent เลือก, หมวดว่างแสดง option เดียว disabled
    "ไม่มีไฟล์ในหมวดนี้" + ข้อความเตือนแยกใต้ dropdown (ตามข้อ 2.2), ปุ่ม
    "คำนวณ" แสดงตลอด disabled ถาวร + hint ว่าจะต่อจริงใน F.4, มี
    showError()/errorBanner กลางสำหรับ google.script.run ล้มเหลว
  - `reference/gsheet/code.gs` — เพิ่ม `doGet()` เดียว เรียก
    `createHtmlOutputFromFile('Index')` ตามสเปคข้อ 4 เป๊ะ (ไม่ใช้
    createTemplateFromFile ตามที่ตกลงไว้)
  ก็อปปี้ทั้งสองไฟล์ไปที่ `D:\MyClasp_SMT_DEMO\` (Index.html ตรงตัว,
  code.gs -> code.js แทนที่ placeholder `myFunction(){}` เดิม) แล้ว byte-diff
  ยืนยันว่าไฟล์ repo กับไฟล์ clasp folder เหมือนกันทุกตัวอักษร
  ไม่แตะ GS_DriveWalker.gs/js หรือไฟล์ engine อื่นใดตามขอบเขต F.3
- คำสั่ง: diff (byte-compare repo vs clasp folder ทั้ง 2 ไฟล์)
- ผล: PASS — diff ว่างทั้งคู่ (ไฟล์ตรงกัน) ยังไม่ได้ทดสอบจริงในเบราว์เซอร์
  (รอผู้ใช้ตรวจไฟล์ก่อนตามมาตรฐานส่วนที่ 3)
- commit: ยังไม่ commit ตามคำสั่งผู้ใช้ (ห้าม commit/push จนกว่าจะตรวจ)
- หมายเหตุ: `code.gs` เป็นไฟล์ใหม่ที่ยังไม่เคย track ใน repo มาก่อน (เดิมมีแต่
  placeholder ใน clasp folder เท่านั้น ไม่มีใน git) — เมื่อ commit จะเป็นไฟล์
  ใหม่ ไม่ใช่การแก้ไฟล์เดิม

## [2026-07-28 20:02] Session F.3 — clasp push หลัง Claude Chat อนุมัติ

- ทำ: Claude (แชท) ตรวจ Index.html + code.gs แล้วอนุมัติ สั่ง `clasp push`
  จาก D:\MyClasp_SMT_DEMO\
- คำสั่ง: clasp push
- ผล: PASS — "Pushed 13 files" รวม code.js (doGet) และ Index.html (cascade UI)
  ใหม่ทั้งคู่ ไฟล์อื่นไม่เปลี่ยน (engine/backend เดิมตามขอบเขต F.3)
- commit: ยังไม่ commit git (รอผู้ใช้ทดสอบผ่าน Test deployments ก่อน)
- หมายเหตุ: ขั้นต่อไปคือเปิด "Test deployments" ในตัว Apps Script editor
  ทดสอบ manual ตาม checklist หัวข้อ 8 ของแผน (หมวดมีข้อมูลจริง +
  หมวดว่าง 7 หมวด) ก่อนค่อย commit

## [2026-07-28 20:45] Session F.3 — commit

- ทำ: Claude (แชท) อนุมัติ git status/diff --stat แล้ว รัน
  `git commit -F .git/smt_commit_msg.txt` (เขียนไฟล์ commit message ผ่าน
  heredoc ใน Bash tool ตามที่ผู้ใช้ยืนยันชัดเจนว่าต้องการแบบนี้ แม้ขัดกับ
  ธรรมเนียมเดิมที่บันทึกไว้ใน memory ว่าใช้ Write tool — cat -A ตรวจแล้วว่า
  LF ล้วน ไม่มี CRLF ปน ก่อน commit)
- คำสั่ง: git commit -F .git/smt_commit_msg.txt ; git log -1 --oneline
- ผล: PASS — commit ecc0a69, 3 files changed (290 insertions)
- commit: ecc0a69
- หมายเหตุ: ยังไม่ push — รอคำสั่งผู้ใช้

## [2026-07-28 21:15] Session F.3 — docs commit (PROJECT_STATE.md + CLAUDE.md)

- ทำ: Claude (แชท) ตรวจ diff ของ CLAUDE.md + PROJECT_STATE.md แล้ว สั่ง commit
  แก้ 2 จุดใน PROJECT_STATE.md (§6 mark F.3 เสร็จ + HEAD, §2 commit-rule
  summary) และ 2 จุดใน CLAUDE.md (§5 มาตรฐาน commit, §7 ข้อ 5 เมนูปุ่ม) —
  กลับกฎ heredoc เดิม (เคยห้ามเพราะ bash tool รัน PowerShell ยุคก่อน ตอนนี้
  รันผ่าน Git Bash แล้ว heredoc+forward slash ใช้ได้จริง ยืนยันจาก F.3)
- คำสั่ง: git add CLAUDE.md PROJECT_STATE.md ; git commit -F
  .git/smt_commit_msg.txt ; git log -1 --oneline
- ผล: PASS — commit b6c7eac, 2 files changed (28 insertions, 8 deletions)
- commit: b6c7eac
- หมายเหตุ: PROJECT_STATE.md §6 ยังมี placeholder
  "<เติม hash หลัง commit นี้จริง>" สำหรับ hash ของ commit นี้เอง (b6c7eac)
  และบรรทัด HEAD ที่เขียนไว้ว่า "ecc0a69 (จะขยับเป็น hash ของ docs commit นี้
  เอง)" ก็ต้องอัปเดตเป็น b6c7eac เช่นกัน — ยังไม่แก้ รอคำสั่งผู้ใช้/Claude แชท
  ว่าจะให้แก้รอบถัดไปหรือปล่อยไว้ก่อน push

## [2026-07-28 21:40] Session F.3 — เติม hash placeholder ใน PROJECT_STATE.md

- ทำ: Claude (แชท) อนุมัติ diff แล้ว commit แก้ placeholder
  "<เติม hash หลัง commit นี้จริง>" ใน §6 เป็น `b6c7eac` จริง + อัปเดตบรรทัด
  HEAD ปัจจุบันของ origin/main เป็น `b6c7eac` (ก้อนเล็กแยกจาก b6c7eac เดิม
  ตามที่ตกลงไว้ ไม่ amend)
- คำสั่ง: git add PROJECT_STATE.md ; git commit -F .git/smt_commit_msg.txt ;
  git log -1 --oneline
- ผล: PASS — commit 2e0c340, 1 file changed (2 insertions, 2 deletions)
- commit: 2e0c340
- หมายเหตุ: local ahead ของ origin/main อยู่ 3 commit แล้ว (ecc0a69, b6c7eac,
  2e0c340) ยังไม่ push รอคำสั่งผู้ใช้

## [2026-07-28 21:55] Session F.3 — push origin/main

- ทำ: push 3 commits ของ Session F.3 ขึ้น origin/main ตามคำสั่งผู้ใช้
- คำสั่ง: git push origin main
- ผล: PASS — 2f30d9b..2e0c340 main -> main
- commit: ecc0a69, b6c7eac, 2e0c340 (ทั้ง 3 อยู่บน origin/main แล้ว)
- หมายเหตุ: Session F.3 ปิดจบสมบูรณ์ (เขียนโค้ด + ทดสอบจริง + commit + push)
  ขั้นต่อไปคือ Session F.4 (เชื่อมปุ่ม "คำนวณ" กับ pipeline เต็ม)

## [2026-07-29 10:19] Session F.4 — สร้าง GS_Pipeline.gs + GS_SheetExport.gs (ตามแผนที่ Claude Chat อนุมัติ)

- ทำ: สร้างไฟล์ใหม่ 2 ไฟล์ตาม `DRAFT_plan_session_F4_calculate_pipeline.md`
  (อนุมัติแล้ว) — ทำทีละไฟล์ ส่งเนื้อหาเต็มให้ผู้ใช้ตรวจในแชทก่อนเขียนจริง
  ทุกไฟล์ ตามที่ผู้ใช้ขอ (ยังไม่ commit — รอไฟล์ที่เหลือ)
  - `reference/gsheet/GS_Pipeline.gs` (ใหม่) — `normalizePiLabels_(rows)`
    (แปลง label "PI1"→"PI-1" เฉพาะคอลัมน์ POINT ก่อนเข้า splitter) +
    `runFullPipeline(fileId, tabName)` (orchestrator: split→parse→build→
    export 3 จุด รวม issues)
  - `reference/gsheet/GS_SheetExport.gs` (ใหม่) — ย้าย
    `exportElementsToSheet()`/`exportCrossCheckToSheet()` จาก
    `D:\MyClasp_SMT_DEMO\TestDrive.js` (ไฟล์ไม่ track ใน git) มาไว้ที่นี่
    เนื้อโค้ดเดิมทุกจุด รวม logic การเขียน tab เป็น helper กลาง `writeTab_()`
    ตัวเดียว (พฤติกรรมเดิมทุกจุด) + เพิ่ม `exportIssuesToSheet()` ใหม่
    (ไม่สร้าง tab ถ้า issues ว่าง, เคลียร์ tab เก่าถ้ามีจาก run ก่อนหน้า)
  - ตรวจ namespace call ในแผน (`GS_TableSplitter`, `GS_PiTableParser`,
    `GS_AlignmentBuilder`, `GS_ElementTable`, `GS_CrossCheck`) ตรงกับของจริง
    ในโค้ดที่มีอยู่แล้วทุกจุด
- คำสั่ง: (ยังไม่รัน test — รอเขียนไฟล์ที่เหลือครบก่อน: แก้ `TestDrive.js`
  ลบ 2 ฟังก์ชันที่ย้ายออก, แก้ `Index.html` ผูกปุ่มคำนวณ)
- ผล: ยังไม่ทดสอบ (รอไฟล์ครบ)
- commit: ยังไม่ commit (ผู้ใช้สั่งหยุดรอก่อนไปไฟล์ที่ 3)
- หมายเหตุ: ทำตามแผนคำต่อคำ (verbatim) ไม่มีการแก้ logic ใดๆ

## [2026-07-29 10:39] Session F.4 — แก้ TestDrive.js + Index.html (ไฟล์ 3-4 ตามแผน)

- ทำ: แก้ 2 ไฟล์ที่เหลือตาม `DRAFT_plan_session_F4_calculate_pipeline.md`
  §4/§6/§7 (อนุมัติแล้ว) — เขียนลงดิสก์ตรงๆ ตามที่ผู้ใช้สั่ง ไม่ paste โค้ด
  ยาวๆ ในแชทอีก
  - `D:\MyClasp_SMT_DEMO\TestDrive.js` — ลบเฉพาะ definition ของ
    `exportElementsToSheet()`/`exportCrossCheckToSheet()` (ย้ายไป
    `GS_SheetExport.gs` แล้วรอบก่อนหน้า) ฟังก์ชันอื่นทั้งหมดไม่แตะ รวม
    `testFullPipelineExportAgainstHorOrr04()`/
    `testFullCrossCheckAgainstHorOrr04()` ที่ยังเรียกชื่อเดิมได้ปกติ
    (global scope เดียวกัน)
  - `reference/gsheet/Index.html` — `calcBtn` เปลี่ยนจาก `disabled` ถาวร
    เป็นผูก `onclick="handleCalcClick()"`, เพิ่ม `handleCalcClick()` (อ่าน
    fileId/tabName, disable dropdown 3 ชั้น+ปุ่ม, เรียก
    `runFullPipeline` ผ่าน `google.script.run`), `onCalcDone(summary)`
    (re-enable ทั้งหมด + สรุปผล elements/issues), `onCalcFail(err)`
    (re-enable ทั้งหมด + เรียก `showError()` เดิมจาก F.3)
  - ส่วนที่ต่างจากตัวอักษรแผนเล็กน้อย (แจ้งผู้ใช้แล้วในแชท): ลบ hint เดิม
    "ปุ่มนี้ยังไม่เชื่อมกับการคำนวณจริง — จะทำใน Session F.4" (กลายเป็นข้อความ
    เท็จหลังผูกปุ่มแล้ว) ใช้ div เดิมนั้นเป็น `#calcStatus` แทนที่จะเพิ่ม div
    ใหม่ซ้อน — ไม่ใช่การเพิ่ม logic ใหม่ แค่ข้อความ/id เปลี่ยน
- คำสั่ง: Edit เท่านั้น (ยังไม่รัน clasp push / test ใดๆ — รอผู้ใช้ตรวจ diff
  ทั้ง 4 ไฟล์ก่อน)
- ผล: ยังไม่ทดสอบ
- commit: ยังไม่ commit (ผู้ใช้สั่งหยุดรอตามแผน)
- หมายเหตุ: ครบ 4 จุดตามแผน F.4 แล้ว (GS_Pipeline.gs, GS_SheetExport.gs,
  TestDrive.js, Index.html) — รอ Claude (แชท) ตรวจไฟล์ 3-4 ก่อนไปขั้นทดสอบจริง

## [2026-07-29 11:35] Session F.4 — clasp push สำเร็จ (รันเองนอก Claude Code) + ยืนยัน appsscript.json ปลอดภัย

- ทำ: อัปเดตสถานะจาก CK1024 — 2 จุดที่ Claude Code เคยรายงานว่าค้างอยู่
  จริงๆ เสร็จไปแล้ว:
  1. `clasp push` สำเร็จแล้ว — รันเองผ่าน Git Bash แยกต่างหาก (ไม่ผ่าน
     Claude Code เนื่องจาก Bash tool ในเซสชันนี้ไม่ใช่ TTY ทำให้ clasp
     ขึ้น "Skipping push." ทุกครั้งตามที่สืบสาเหตุไว้ก่อนหน้า) ผล: Pushed 15
     files รวม `GS_Pipeline.js`/`GS_SheetExport.js`/`Index.html`/
     `TestDrive.js` ของ F.4 ครบ
  2. เช็ค `appsscript.json` บน Apps Script online editor เทียบกับ Claude
     (แชท) แล้ว — เนื้อหาตรงกับ local ทุกตัวอักษร ไม่มี field เกิน (ไม่มี
     `webapp`/deployment config ที่ local ขาด) ยืนยันว่าความกังวลเรื่อง
     `--force` ไปทับ config ของ Test deployment (F.3) ไม่เป็นปัญหาจริง
- คำสั่ง: (รันนอก Claude Code ทั้งหมด — ไม่มีคำสั่งฝั่งนี้)
- ผล: PASS — push สำเร็จ 15/15 ไฟล์
- commit: ยังไม่ commit (รอทดสอบผ่าน checklist ก่อน)
- หมายเหตุ: งานที่ค้างจริงตอนนี้เหลือแค่ 2 จุด — (1) ทดสอบผ่าน Test
  deployments ตาม checklist หัวข้อ 9 ของ
  `DRAFT_plan_session_F4_calculate_pipeline.md` (คำนวณ HOR-ORR-04 ไม่มี
  issues, อัปโหลด SettingOutTest_Part_2.csv ทดสอบ normalizer, กดคำนวณซ้ำ 2
  ครั้ง, เช็ค dropdown/ปุ่ม disable ด้วยตา) (2) commit git หลังทดสอบผ่านครบ

## [2026-07-29 12:10] เขียนทับ DEPENDENCY_MAP.md + PROJECT_STATE.md ตามที่ Claude (แชท) ร่างมา — ยังไม่ commit

- ทำ: เขียนทับ 2 ไฟล์เอกสารสถานะโปรเจกต์ตามเนื้อหาที่ Claude (แชท) ร่าง+ตรวจ
  มาให้ (หา/แทนที่ตรงตัวเป๊ะทุกจุด ไม่ใช่ Claude Code แต่งเอง):
  1. `DEPENDENCY_MAP.md` — 4 จุด: (1) scope header เพิ่ม GS_DriveWalker/
     GS_SheetExport/GS_Pipeline + note bundle เลิกใช้ (2) เพิ่ม 2 แถวตาราง
     GS_SheetExport.gs/GS_Pipeline.gs (3) เพิ่ม 2 bullet transitive closure
     (4) เพิ่มย่อหน้าท้ายไฟล์อธิบาย 15 ไฟล์ clasp + ประกาศเลิกใช้ BUNDLE_*.md
     — Claude (แชท) ตรวจ diff แล้วอนุมัติ (เขียนทับ+ตรวจผ่านสมบูรณ์)
  2. `PROJECT_STATE.md` — เขียนทับทั้งไฟล์ (header วันที่, ตาราง §3 เพิ่ม
     GS_SheetExport.gs/GS_Pipeline.gs, §4 ข้อ 6-7 แก้ให้ตรงว่าฟังก์ชัน export
     ย้ายไป GS_SheetExport.gs แล้ว, §6 แถว F + section ใหม่ "Session F.4 —
     สถานะ ณ handoff" + roadmap F.3 ขีดฆ่า F.4 ระบุสถานะ, §7 เพิ่ม 2 บรรทัด
     backlog, §8 เปลี่ยนตัวอย่างข้อความเริ่ม session) — รอ Claude (แชท) ตรวจ
     diff รอบนี้ก่อน
  - ระหว่างทางมีรอบ Edit tool ถูกปฏิเสธหลายครั้ง (ผู้ใช้อยากเห็น `git diff`
    เป็น text ในเทอร์มินัลก่อน ไม่เอา preview ในแชท) — แก้เป็นใช้ Write
    เขียนทับทั้งไฟล์ตรงจากเนื้อหาที่ผู้ใช้แปะในแชท แล้วรัน `git diff` ยืนยัน
    แทน ตาม feedback memory "show diff before save"
- คำสั่ง: `git diff DEPENDENCY_MAP.md`, Write (เขียนทับ DEPENDENCY_MAP.md),
  `git diff DEPENDENCY_MAP.md` (ยืนยันรอบสอง), Write (เขียนทับ
  PROJECT_STATE.md — ครั้งแรก error "file modified since read", Read ใหม่
  พบว่าเนื้อหาตรงเป้าหมายอยู่แล้ว), `git diff PROJECT_STATE.md`
- ผล: DEPENDENCY_MAP.md — PASS, Claude (แชท) อนุมัติแล้ว. PROJECT_STATE.md —
  diff ตรงตามที่ร่างไว้ทุกจุด รอ Claude (แชท) ตรวจ
- commit: ยังไม่ commit ทั้ง 2 ไฟล์ (ตามคำสั่งผู้ใช้)
- หมายเหตุ: ไม่มีการแก้ไฟล์โค้ด/engine ใดๆ ในรอบนี้ เป็นเอกสารสถานะล้วน

## [2026-07-29 12:25] Claude (แชท) อนุมัติ PROJECT_STATE.md แล้ว — เอกสารทั้ง 2 ไฟล์ผ่านหมด รอทดสอบ F.4

- ทำ: บันทึกผลอนุมัติจาก Claude (แชท) — ตรวจไฟล์จริง PROJECT_STATE.md ผ่าน
  สมบูรณ์ (ต่อจาก DEPENDENCY_MAP.md ที่อนุมัติไปก่อนหน้าใน entry 12:10)
  สรุปสถานะเอกสาร: DEPENDENCY_MAP.md ✅ อนุมัติแล้ว, PROJECT_STATE.md ✅
  อนุมัติแล้ว — ทั้ง 2 ไฟล์ยังไม่ commit ตามคำสั่งผู้ใช้ รอทดสอบ F.4 ผ่าน
  checklist (Test deployments) ก่อนจึงจะ commit รวมกัน
- คำสั่ง: (ไม่มีคำสั่งรันเพิ่มรอบนี้ — แค่ log ผลอนุมัติ)
- ผล: PASS (เอกสารสถานะ 2/2 ไฟล์ผ่านการตรวจจาก Claude (แชท))
- commit: ยังไม่ commit — รอ CK1024 ทดสอบ F.4 ผ่าน Test deployments ก่อน
- หมายเหตุ: งานที่ค้างจริงตอนนี้เหมือนเดิมคือ 2 จุด — (1) ทดสอบผ่าน Test
  deployments ตาม checklist หัวข้อ 9 ของ
  `DRAFT_plan_session_F4_calculate_pipeline.md` (2) commit git รวมทั้งโค้ด
  F.4 (GS_Pipeline.gs/GS_SheetExport.gs/TestDrive.js/Index.html) และเอกสาร
  สถานะ 2 ไฟล์ (DEPENDENCY_MAP.md/PROJECT_STATE.md) หลังทดสอบผ่านครบ —
  CK1024 ไปทดสอบเองต่อ ไม่มีงานฝั่ง Claude Code ต่อในรอบนี้

## [2026-07-29] Commit F.4 pipeline wiring — เฉพาะโค้ด 4 ไฟล์ (ยังไม่รวมเอกสารสถานะ)

- ทำ: หลังทดสอบผ่าน Test deployments ครบ (HOR-ORR-04 + SettingOutTest_Part_2.csv
  ยืนยันตามรายละเอียดในหัวข้อ commit message) เขียน commit message ผ่าน
  bash heredoc ไปที่ `.git/smt_commit_msg.txt` (2 รอบ — รอบแรกพบว่าอ้างถึง
  TestDrive.js ราวกับเป็นไฟล์ git-tracked ทั้งที่จริงเป็นไฟล์ clasp-folder
  เท่านั้น ไม่เคย track ใน git ตั้งแต่แรก แก้บรรทัดนั้นแล้วเขียนทับใหม่ทั้งไฟล์
  ด้วย heredoc ตามคำสั่งผู้ใช้ ไม่ใช้ Edit tool) ตรวจ `cat -A` ผ่านทั้ง 2 รอบ
  (LF ล้วน ไม่มี CRLF ปน) — `git add` เฉพาะ 4 ไฟล์ตามคำสั่งชัดเจนของผู้ใช้
  (`GS_Pipeline.gs`, `GS_SheetExport.gs`, `Index.html`, `session_logs/latest.md`)
  ไม่แตะ `DEPENDENCY_MAP.md`/`PROJECT_STATE.md` (คนละ commit ตามที่สั่ง) —
  ส่งผล `git status` + `git diff --cached --stat` ให้ Claude (แชท) ตรวจก่อน
  commit จริง
- คำสั่ง: heredoc เขียน `.git/smt_commit_msg.txt` (2 รอบ), `cat -A
  .git/smt_commit_msg.txt`, `git add reference/gsheet/GS_Pipeline.gs
  reference/gsheet/GS_SheetExport.gs reference/gsheet/Index.html
  session_logs/latest.md`, `git status`, `git diff --cached --stat`,
  `git commit -F .git/smt_commit_msg.txt`, `git log -1 --oneline`
- ผล: PASS — commit `51f3818` (4 files changed, 294 insertions(+), 2
  deletions(-))
- commit: `51f3818`
- หมายเหตุ: ยังไม่ push (ผู้ใช้ยังไม่สั่ง) — `DEPENDENCY_MAP.md`/
  `PROJECT_STATE.md` (อนุมัติแล้วจาก Claude (แชท) ตาม entry 12:25) ยังรอ
  commit แยกต่างหากตามคำสั่งผู้ใช้ ไม่รวมในรอบนี้

## [2026-07-29] Docs commit — DEPENDENCY_MAP.md + PROJECT_STATE.md (หลัง Claude (แชท) อนุมัติไฟล์จริง)

- ทำ: เขียนทับ `PROJECT_STATE.md` เต็มไฟล์ด้วย Write tool ตรงๆ (ไม่ผ่าน Edit)
  ตามเนื้อหาที่ Claude (แชท) ร่างมา ส่ง `git diff PROJECT_STATE.md` ให้ตรวจ
  ก่อน — CK1024 อัปโหลดไฟล์จริงกลับไปให้ Claude (แชท) ตรวจรอบสุดท้ายจนอนุมัติ
  แล้ว จากนั้นเขียน commit message ผ่าน bash heredoc ไปที่
  `.git/smt_commit_msg.txt` (3 รอบ — รอบแรก/สองไม่มีบรรทัดว่างคั่นระหว่าง
  หัวข้อกับ bullet แรกจริง ทั้งที่เนื้อหาที่พิมพ์ดูเหมือนมี แก้ให้เขียนทับใหม่
  จนรอบสามตรวจ `cat -A` เห็นบรรทัดว่าง (`$` โดดๆ) คั่นอยู่จริง) — `git add`
  เฉพาะ 2 ไฟล์ (`DEPENDENCY_MAP.md`, `PROJECT_STATE.md`) ไม่แตะ
  `session_logs/latest.md` ที่มี entry ค้างจากรอบก่อน — ส่งผล `git status` +
  `git diff --cached --stat` ให้ Claude (แชท) ตรวจก่อน commit จริง
- คำสั่ง: Write เขียนทับ `PROJECT_STATE.md`, `git diff PROJECT_STATE.md`,
  heredoc เขียน `.git/smt_commit_msg.txt` (3 รอบ), `cat -A
  .git/smt_commit_msg.txt`, `git add DEPENDENCY_MAP.md PROJECT_STATE.md`,
  `git status`, `git diff --cached --stat`, `git commit -F
  .git/smt_commit_msg.txt`, `git log -1 --oneline`
- ผล: PASS — commit `0656528` (2 files changed, 88 insertions(+), 41
  deletions(-))
- commit: `0656528`
- หมายเหตุ: local ahead ของ `origin/main` ตอนนี้ 2 commits (`51f3818` feat +
  `0656528` docs) ยังไม่ push — `session_logs/latest.md` ยังมีการแก้ค้างอยู่
  (entry บันทึกผล commit ก่อนหน้า + entry นี้เอง) ยังไม่ commit รอคำสั่งถัดไป

## [2026-07-29] Commit ก้อนที่ 3 — เติม hash placeholder ของ docs commit เอง (0656528) ลง PROJECT_STATE.md

- ทำ: เขียนทับ `PROJECT_STATE.md` เต็มไฟล์ด้วย Write tool ตรงๆ อีกรอบ (ไม่ผ่าน
  Edit) เติม hash `0656528` แทน placeholder ที่ตอน commit `0656528` เอง
  ยังไม่รู้ค่าจริง (เทคนิคเดียวกับที่เคยทำกับ `b6c7eac`→`2e0c340` ของ F.3) —
  ส่ง `git diff PROJECT_STATE.md` ให้ตรวจก่อน จากนั้นเขียน commit message
  ผ่าน bash heredoc ไปที่ `.git/smt_commit_msg.txt` (2 รอบ — รอบแรกไม่มี
  บรรทัดว่างคั่น subject/body จริง แก้ให้เขียนทับใหม่) ตรวจ `cat -A` พบ
  `M-BM-'6`/`M-bM-^@M-^T` (escape ของ `§`/em-dash) จึง `xxd` ตรวจ byte จริง
  ยืนยันว่าเข้ารหัส UTF-8 ถูกต้องสมบูรณ์ (`§`=`c2 a7`, em-dash=`e2 80 94`) —
  ไม่ใช่ไฟล์เพี้ยน แค่พฤติกรรมปกติของ `cat -A` กับไบต์ non-ASCII — `git add
  PROJECT_STATE.md` แล้วส่งผลให้ Claude (แชท) ตรวจก่อน commit จริง
- คำสั่ง: Write เขียนทับ `PROJECT_STATE.md`, `git add PROJECT_STATE.md`,
  heredoc เขียน `.git/smt_commit_msg.txt` (2 รอบ), `cat -A
  .git/smt_commit_msg.txt`, `xxd .git/smt_commit_msg.txt`, `git commit -F
  .git/smt_commit_msg.txt`, `git log -3 --oneline`
- ผล: PASS — commit `a6bd9f6` (1 file changed, 12 insertions(+), 12
  deletions(-))
- commit: `a6bd9f6`
- หมายเหตุ: local ahead ของ `origin/main` ตอนนี้ 3 commits (`51f3818` feat,
  `0656528` docs, `a6bd9f6` hash-fill) ยังไม่ push — รอคำสั่งถัดไป

## [2026-07-29] Push F.4 ทั้ง 3 commit ขึ้น origin/main

- ทำ: push commit ทั้ง 3 ก้อนของ Session F.4 (`51f3818` feat, `0656528` docs,
  `a6bd9f6` hash-fill) ขึ้น `origin/main` ตามคำสั่งผู้ใช้โดยตรง
- คำสั่ง: `git push origin main`
- ผล: PASS — `2e0c340..a6bd9f6 main -> main`
- commit: (push ไม่ใช่ commit ใหม่ — เป็นแค่ sync ของ 3 commit ที่มีอยู่แล้ว
  ไปยัง remote)
- หมายเหตุ: `origin/main` และ local `main` ตรงกันแล้วที่ `a6bd9f6` — F.4 ปิด
  จบสมบูรณ์ทั้งโค้ด+เอกสาร+push ขั้นต่อไปคือ F.5 (Deploy web app จริง)

## [2026-08-01] Session F.5 ส่วน A (error handling) + ส่วน B (deploy guide) — commit

- ทำ: ทำตามแผนที่อนุมัติแล้ว (`session_logs/plan_20260729_1933.md`) ครบทั้ง 2
  ส่วน — ส่วน A แก้ `reference/gsheet/Index.html` เพิ่มฟังก์ชัน pure
  `getFriendlyMessage()` (ไล่ regex 8 เคสตามตาราง A.3 ของแผน เรียงจากเฉพาะเจาะจง
  ไปหา catchall) และปรับ `showError()` ให้แสดงข้อความ friendly ก่อน ตามด้วย
  `<details>` แบบพับเก็บป้ายกำกับ "รายละเอียดทางเทคนิค (สำหรับแจ้งผู้ดูแลระบบ)"
  เก็บ raw error message เดิมไว้ครบทุกตัวอักษร (ไม่แตะไฟล์ `.gs` ใดๆ ตามแผน) —
  ส่วน B สร้างไฟล์ใหม่ `docs/DEPLOY_GUIDE.md` คู่มือภาษาไทย 4 ขั้นตอน (ทำสำเนา →
  deploy เป็น New deployment → ขอสิทธิ์เข้าถึง Google Sheet → เปิดใช้งาน) เน้น
  เตือนเรื่อง "Who has access = Only myself" เป็นค่าเริ่มต้นเสมอ และห้ามใช้ Test
  deployments
- ทดสอบ: (1) คัดลอก `getFriendlyMessage()` ไปรันแยกด้วย Node ป้อน raw message
  ครบทั้ง 8 เคสตามตาราง A.3 ของแผน — ผ่านครบ 8/8 ตรงกับข้อความที่ออกแบบไว้ (ลบ
  scratchpad script ทิ้งหลังทดสอบผ่าน ไม่ commit) (2) รัน
  `node reference/gsheet/smoke_test.js` ยืนยันไม่กระทบของเดิม ผ่าน 23/23 (3)
  ทดสอบ error banner จริงในเบราว์เซอร์ — เจอ catchall case จริงระหว่างทดสอบ (ไม่
  ตรง 8 เคสที่ออกแบบไว้ล่วงหน้า) banner แสดงข้อความ friendly ถูกต้อง +
  รายละเอียดทางเทคนิคเก็บ raw message ไว้ครบใน `<details>` — CK1024 ตัดสินใจว่า
  เพียงพอแล้วสำหรับ A.6 ข้อ 3 ไม่ต้องบังคับให้เกิด 2 เคสที่วางแผนไว้เดิม (tab not
  found / permission) อีก
- คำสั่ง: `node` (scratchpad script ทดสอบ 8 เคส), `node
  reference/gsheet/smoke_test.js`, ทดสอบ manual banner ในเบราว์เซอร์จริง
- ผล: PASS ทั้งหมด (8/8 mapping cases, 23/23 smoke test, banner จริงถูกต้อง)
- commit: (placeholder — ทราบค่าจริงหลัง commit รอบนี้ จะเติมใน entry แยกภายหลัง
  ถ้าจำเป็น เหมือนที่เคยทำกับ `PROJECT_STATE.md` ใน F.4)
- หมายเหตุ: **บั๊กค้างพบระหว่างทดสอบ (บันทึกไว้ก่อนตามคำสั่ง CK1024 — ยังไม่แก้ ยก
  ไป session ถัดไป)** — เกิด `TypeError: Cannot read properties of undefined
  (reading 'n')` ตอนเลือก sheet/tab ที่ว่างเปล่าไม่มีข้อมูล ไม่เข้าเคสไหนใน 8
  เคส raw→friendly ที่ออกแบบไว้ ตกไปที่ catchall ซึ่งทำงานถูกต้องตามที่ออกแบบ
  (แสดง friendly message + raw message ครบ) แต่ root cause ของ TypeError เอง
  (แถวไหนใน `.gs` ที่พยายามอ่าน `.n` จาก object undefined) ยังไม่ได้สืบ ยังไม่แก้
  — ยังไม่ push (รอ CK1024 ส่ง commit hash ให้ Claude (แชท) อนุมัติก่อน)
