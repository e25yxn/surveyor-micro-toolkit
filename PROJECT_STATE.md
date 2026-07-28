# PROJECT_STATE.md — SMT (Surveyor Micro Toolkit) สถานะปัจจุบัน

**เอกสารนี้คือ "สแนปช็อตสถานะปัจจุบัน" — เขียนทับใหม่ทุกครั้งที่จบ session
(ต่างจาก `session_logs/latest.md` ที่เป็นบันทึกย้อนหลังทุก session)**
**อัปเดตล่าสุด: 2026-07-27, หลังจบ Session E, เริ่ม Session F**

---

## 1. ภาพรวมโปรเจกต์

SMT = Python library คำนวณ horizontal road alignment (ทางตรง/โค้ง/spiral)
ล้วนๆ พอร์ตไปเป็น Excel VBA และ Google Apps Script ด้วย เป้าหมาย: เครื่องมือ
สำรวจที่ตรวจสอบได้อิสระ ลดการพึ่งซอฟต์แวร์อัตโนมัติเกินไป

- Repo: https://github.com/e25yxn/surveyor-micro-toolkit
- Local repo: `D:\My Second Project\SurveyorMicroToolkit\`
- Demo Apps Script project: `SMT_COGO_DEMO`, clasp folder `D:\MyClasp_SMT_DEMO`
  (แยกจาก sandbox เดิม `SMT_COGO` ที่ `D:\MyClasp_verify`)
- ข้อมูลทดสอบจริง: Google Sheet `HOR-ORR-04`
  (ID `1rEGH78P6vceamCIAUOVxKJSmAmK7aujnsY8iH3OcKsA`) — 36 แถว ข้อมูลถูกต้องครบ

---

## 2. โครงสร้าง 3 ฝ่าย (Plan-Review-Approve)

- **CK1024** (คุณ) — เจ้าของโปรเจกต์ ผู้ตัดสินใจ ตรวจทุก step ก่อนอนุมัติ
- **Claude Chat** — ที่ปรึกษา/โค้ช วางแผน ตรวจโค้ด verify ด้วยการรันจริง
  (Python/Node ในเครื่องตัวเอง) ก่อนอนุมัติให้ Claude Code เขียนไฟล์จริง
- **Claude Code** — ผู้ปฏิบัติงานจริง เข้าถึงไฟล์ในเครื่อง CK1024 ได้ตรง

**กฎเหล็ก**: ห้าม Claude Code เขียนไฟล์จริงโดยไม่ผ่านการตรวจจาก Claude Chat
ก่อนเสมอ (ยกเว้นไฟล์ scratch ชั่วคราวนอก repo) — commit message ผ่าน
`.git/smt_commit_msg.txt` ด้วย heredoc ผ่าน Git Bash เท่านั้น (forward slash
เสมอ ห้าม backslash — ถ้า Write tool ถาม overwrite ไฟล์นี้ตรงๆ ให้กด No)
ตรวจ `cat -A` ก่อน commit ทุกครั้ง — ดูรายละเอียดเต็มใน `CLAUDE.md`

---

## 3. ไฟล์ GAS ที่มีอยู่แล้ว (`reference/gsheet/` + `reference/`)

| ไฟล์ | สถานะ | Depends on | หมายเหตุ |
|---|---|---|---|
| `FPMath.gs` | ✅ verified (pre-project) | ไม่มี | ชั้นล่างสุด: มุม, ปัดเศษ, angleDiff |
| `WCB.gs` | ✅ verified (pre-project) | FPMath | azimuth, distance2D |
| `GS_Alignment.gs` | ✅ verified (pre-project) | FPMath, WCB | makeElement, exitState, stationToCoord — engine เรขาคณิตหลัก |
| `GS_AlignmentBuilder.gs` | ✅ verified (pre-project, Groups A/B/C) | FPMath, WCB, GS_Alignment | `buildFromPI()` — v2.0 มี EXT-001 (angle point) + EXT-003 (spiral) — **นี่คือ oracle ที่ถูกต้อง** ไม่ใช่ `reference/AlignmentBuilder.gs` (v1.1 เก่า ไม่ได้ใช้) |
| `GS_TableSplitter.gs` | ✅ Session (ก่อนบทสนทนานี้), verify diff=0 | ไม่มี | `splitMixedAlignmentTable(rows)` → `{vertexRows, drawing}` |
| `GS_PiTableParser.gs` | ✅ Session B, verify diff=0 | ไม่มี | `parsePiTable(vertexRows)` → vertices array |
| `GS_ElementTable.gs` | ✅ Session D, verify diff=0 | FPMath | `elementsToRows(elements)` → ตาราง 8 คอลัมน์ |
| `GS_CrossCheck.gs` | ✅ Session E, verify diff=0 (2a) + prototype (2b/2c) | FPMath, WCB, GS_Alignment | `checkPoints()`/`checkPiCurves()` → 3 ตาราง cross-check |
| `GS_DriveWalker.gs` | ✅ Session F.2, verified live (2026-07-28) | GS_ElementTable, GS_CrossCheck (+ transitively FPMath, WCB, GS_Alignment) | `listCategoryFolders()`/`listFilesInFolder(folderId)`/`listAlignmentTabsInFile(fileId)` — เดิน Drive สดทุกครั้ง (ไม่ hardcode) รองรับ folder/file/tab ที่ผู้ใช้เพิ่มได้อิสระตลอดเวลา, เรียงผลลัพธ์ตามชื่อ (alphabetical) |

**Pipeline เต็ม**: `splitMixedAlignmentTable(rows)` → `parsePiTable(vertexRows)`
→ `buildFromPI(vertices)` → `{elements, control, issues}` → export ผ่าน
`GS_ElementTable`/`GS_CrossCheck`

**ทั้งหมด push เข้า `D:\MyClasp_SMT_DEMO\` แล้ว** (10 ไฟล์ .js/.gs +
`appsscript.json` + `code.js` = 12 ไฟล์ตอนล่าสุด)

---

## 4. `TestDrive.js` (`D:\MyClasp_SMT_DEMO\TestDrive.js`) — ฟังก์ชันทดสอบที่มี

1. `testExploreFolders()` — เดินโฟลเดอร์ Drive (FOLDER_ID เก่าคือของ
   `SMT_Web_App_demo` ไม่ใช่ `001_Hor_Align`)
2. `inspectHorAlignStructure()` — list tab/header/sample ของสเปรดชีตที่ผูก
3. `testSplitAgainstHorOrr04()` — verify `GS_TableSplitter`
4. `testParseAgainstHorOrr04()` — verify `GS_PiTableParser`
5. `testBuildFromPIAgainstHorOrr04()` — verify `buildFromPI`
6. `exportElementsToSheet(ss, alignmentName, elements)` + `testFullPipelineExportAgainstHorOrr04()` — Session D, **parameterize แล้วใน Session F.1** (เขียนไป tab `result_(alignmentName)_Elements`)
7. `exportCrossCheckToSheet(ss, alignmentName, elements, drawing, rows, vertices, control)` + `testFullCrossCheckAgainstHorOrr04()` — Session E, **parameterize แล้วใน Session F.1** (เขียนไป 3 tab `result_(alignmentName)_CrossCheck_Points/Radius/Deflection`)
8. `dumpRawHorOrr04()` — dump 36 แถวดิบจากชีตจริง
9. `testListCategoryFolders()` — verify `listCategoryFolders` (Session F.2)
10. `testListFilesInFolder()` — verify `listFilesInFolder` (Session F.2)
11. `testListAlignmentTabsInFile()` — verify `listAlignmentTabsInFile` (Session F.2)

**หมายเหตุสำคัญ**: `SPREADSHEET_ID` เดิมที่เข้าใจผิดว่าเป็น
`SMT_COGO_Builder_DEMO` แท้จริงคือไฟล์ **`HOR-ORR-04` เอง**
(`1rEGH78P6vceamCIAUOVxKJSmAmK7aujnsY8iH3OcKsA`) — ยืนยันจาก `ss.getName()`
จริงแล้ว ID จริงของ `SMT_COGO_Builder_DEMO` ยังไม่ทราบ (ไม่กระทบงานที่ผ่านมา)

---

## 5. Python core ที่เกี่ยวข้อง (`src/smt/`)

| ไฟล์ | ฟังก์ชันที่ใช้อ้างอิง |
|---|---|
| `fpmath.py` | `normalize_angle`, `calculate_angle_diff`, `rad_to_deg`, `deg_to_rad` |
| `wcb.py` | `calculate_azimuth`, `calculate_distance_2d` |
| `alignment.py` | `Element`, `make_element`, `calculate_exit_state`, `calculate_station_to_coordinate` |
| `builders/table_splitter.py` | `split_mixed_alignment_table()` — **ห้ามแก้** |
| `builders/alignment_builder.py` | `parse_pi_table()`, `build_alignment_from_pi()`, `check_against_drawing()` — **ห้ามแก้ทั้งหมด** |
| `check.py` | `check_horizontal()` (oracle ของตาราง 2a), `bulk_cross_check()` (คนละงาน — inverse sta/offset ไม่เกี่ยว), `check_vertical()` |
| `cli.py` | `_run_build()`/`_radius_from_element()` (บรรทัด 109-168, oracle ของตารางที่ 1) |

---

## 6. ความคืบหน้า Session (element export feature)

| Session | เนื้อหา | สถานะ | Commit |
|---|---|---|---|
| A | สำรวจ Python core | ✅ | `6728276` |
| B | พอร์ต `parse_pi_table()` | ✅ | `a4a094b`, `2b33059` |
| C | Wire pipeline เต็ม | ✅ | `6246cdf` |
| D | Export ตารางที่ 1 | ✅ | `b3e5926`, `118234b` |
| E | Export ตารางที่ 2 (3 ตาราง) | ✅ | `d9d95e6`, `ced10c2`, `de223b2` |
| **F** | **หน้าเว็บจริง (`doGet()`+HTML)** — F.1-F.3 เสร็จ, F.4 กำลังทำต่อ | 🔵 **กำลังทำ** | F.1-F.2: HEAD ผ่าน `9e5e608`; F.3 (feat): `ecc0a69`; F.3 (docs): `b6c7eac` |

**HEAD ปัจจุบันของ `origin/main`**: `b6c7eac`

### Session F.3 — เสร็จแล้ว (2026-07-28)

`doGet()` + `Index.html` cascade UI (หมวด→ไฟล์→alignment tab) ตามสเปคที่ยืนยันไว้
ด้านบนครบทุกข้อ — dropdown ทั้ง 3 ชั้นแสดงตลอด disabled+placeholder รอข้อมูล,
หมวด/ไฟล์ว่างแสดงทั้ง option เดียว disabled + ข้อความเตือนแยก, ปุ่ม "คำนวณ"
disabled ถาวร (รอ F.4), central `showError()` จับ `google.script.run` fail
ทดสอบผ่านจริงผ่าน Test deployments แล้ว (`001_Hor_Align` ไล่ครบ 3 ชั้น, หมวดว่าง
7 หมวดแสดงถูกต้อง) ไฟล์: `reference/gsheet/Index.html` (ใหม่),
`reference/gsheet/code.gs` (ใหม่) — ไม่แตะ engine/backend ใดๆ

### Session F — ดีไซน์ที่ยืนยันแล้ว (ยังไม่เขียนโค้ด)

1. **Cascade เต็มรูปแบบ v1**: Drive folder → Google Sheets file → Sheet tab
   (ชื่อ tab = ชื่อ alignment) — แม้ตอนนี้มีแค่ 1 alignment จริง **หมวด/ไฟล์/tab
   ทั้งหมดเดินหาสดจาก Drive จริงทุกครั้ง ไม่ hardcode รายชื่อไว้ที่ไหนเลย —
   จำนวนเปลี่ยนแปลงได้ตลอดตามที่ผู้ใช้เพิ่มเอง (ยืนยันจาก F.2 live test: เจอ 8
   หมวดจริง ไม่ใช่ 6-7 ตามที่เคยประมาณไว้)**
2. **ปุ่ม "คำนวณ" รันจริง**: split→parse→build→export เต็ม pipeline ทุกครั้ง
   ที่กด ไม่ใช่แค่โชว์ผลเก่า
3. **ผลลัพธ์**: เขียนกลับเข้าไฟล์เดียวกับข้อมูลต้นทาง (ไม่ใช่ไฟล์แยก) เป็น
   **4 tab แยกกัน** เติมชื่อ alignment นำหน้า:
   `result_(alignment)_Elements`, `result_(alignment)_CrossCheck_Points`,
   `result_(alignment)_CrossCheck_Radius`, `result_(alignment)_CrossCheck_Deflection`
   — ต้องปรับ `exportElementsToSheet()`/`exportCrossCheckToSheet()` ให้รับ
   `ss` + ชื่อ alignment เป็น parameter แทน hardcode

### แผนขั้นย่อยที่เสนอไว้

~~F.1 ปรับ export functions ให้ parameterize~~ **(เสร็จแล้ว)** →
~~F.2 ฟังก์ชัน backend เดิน Drive (list folder/file/tab)~~ **(เสร็จแล้ว)** →
F.3 `doGet()`+HTML cascade UI → F.4 เชื่อมปุ่มคำนวณกับ pipeline →
F.5 Deploy web app จริง → F.6 ทดสอบ end-to-end

---

## 7. Backlog / ค้างไว้ไม่เร่งด่วน

- `multicurve.py` solver — รอ CK1024 ให้ scope ก่อน ห้ามสืบเองก่อนถาม
- 4 ไฟล์ untracked ยังไม่ตัดสินใจเก็บ/ลบ: `elements_for_excel.csv`,
  `reference/vba/VBA_Phase4_COSINE_TestChecklist.xlsx`,
  `test_data/SMT_TEST_CLOTHIOD.csv`, `test_data/SettingOutTest555.xml`
- ID จริงของ `SMT_COGO_Builder_DEMO` ยังไม่ทราบ
- `docs/extensions.md`/`GS_AlignmentBuilder.gs` comment เรื่อง Group C
  Sheets-verification ยังไม่อัปเดต
- `clasp run-function`/`clasp logs` ยังใช้ไม่ได้ — รันทดสอบผ่าน Apps Script
  web editor แทนเสมอ

---

## 8. ข้อความเริ่ม session ใหม่ (ตัวอย่าง)

```
นี่คือ PROJECT_STATE.md ล่าสุดของโปรเจกต์ SMT (แนบไฟล์) — ทำ Session F ต่อจาก
ขั้น F.1 (ปรับ exportElementsToSheet/exportCrossCheckToSheet ให้ parameterize)
ตามที่ยืนยันไว้แล้ว
```
