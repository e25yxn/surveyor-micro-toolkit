# DRAFT_plan_session_F4_calculate_pipeline.md

**สถานะ: ร่างรอตรวจ (Plan) — ยังไม่ส่งให้ Claude Code เขียนไฟล์จริง**
**เขียน 2026-07-29 หลังคุยสเปคกับ CK1024**

---

## 1. เป้าหมาย F.4

เชื่อมปุ่ม "คำนวณ" ใน `Index.html` เข้ากับ pipeline เต็ม
(split→parse→build→export) ตามที่ยืนยันไว้ใน Session F design เดิม

---

## 2. สเปคที่ยืนยันแล้ว (2026-07-29)

1. ระหว่างคำนวณ: disable dropdown ทั้ง 3 ชั้น + ปุ่มคำนวณ (กันกดซ้ำ/เปลี่ยน
   ระหว่างรัน)
2. หลังคำนวณเสร็จ: โชว์สรุปสั้นๆ (จำนวน elements + จำนวน issues ที่เจอ)
3. `issues` (จาก `buildFromPI()`) เขียนลง tab ใหม่ `result_(alignment)_Issues`
   สร้างเฉพาะตอนมี issues จริง — ถ้ารันซ้ำแล้วไม่มี issues แต่ tab เก่ายังอยู่
   จาก run ก่อนหน้า ให้เคลียร์เนื้อหาทิ้ง (กันข้อมูลเก่าค้างหลอกผู้ใช้)
4. กดคำนวณซ้ำทับผลเดิมได้เลยไม่ต้องขึ้นเตือนยืนยัน (ตรงกับดีไซน์เดิม
   "รันจริงทุกครั้ง ไม่ใช่โชว์ผลเก่า")
5. PI label ที่ไม่มีขีดกลาง (`PI1` แทน `PI-1`) ต้องถูก normalize อัตโนมัติ
   ก่อนเข้า splitter — **ไม่แก้** `split_mixed_alignment_table()`/
   `GS_TableSplitter.gs` (ห้ามแก้ตาม `PROJECT_STATE.md` §5) แต่เพิ่ม adapter
   function ใหม่ทำหน้าที่แปลงก่อนส่งเข้า
6. (แจ้งไว้ล่วงหน้า ไม่ใช่งานของ F.4) — จะพอร์ต normalizer นี้ไป Python core
   ด้วยทีหลัง หลัง F.4 เสร็จ ให้เป็นมาตรฐานเดียวกันทั้งสองภาษา

---

## 3. จุดที่ต้องตัดสินใจก่อนร่างโค้ดจริง (เจอระหว่างวางแผน)

**`exportElementsToSheet()`/`exportCrossCheckToSheet()` อยู่ผิดที่**

ปัจจุบันสองฟังก์ชันนี้อยู่ใน `TestDrive.js` เท่านั้น ซึ่งเป็นไฟล์ที่**ไม่ track
ใน git** (`D:\MyClasp_SMT_DEMO\TestDrive.js` เท่านั้น — ดู `PROJECT_STATE.md`
§3) ถ้าปุ่มคำนวณจริง (production path) ต้องเรียกใช้ฟังก์ชันที่อยู่ในไฟล์ทดสอบ
ที่ไม่ track — repo ที่ clone ใหม่ (เช่นตอนเปิดเป็น open-source ให้ทีมงาน
รุ่นน้องใช้ ตามเป้าหมายที่วางไว้ตั้งแต่ต้น) จะขาดฟังก์ชันสำคัญไปเลย

**เสนอ**: ย้าย (move ไม่ใช่ copy) สองฟังก์ชันนี้ออกจาก `TestDrive.js` ไปไฟล์ใหม่
ที่ track จริง `reference/gsheet/GS_SheetExport.gs` — เนื้อโค้ดเดิมทุกตัวอักษร
ไม่แก้ logic อะไรเลย (แค่ย้ายที่อยู่) `TestDrive.js` ยังเรียกใช้ได้ปกติเพราะ
Apps Script ใช้ global scope เดียวกันทั้งโปรเจกต์ (ไม่มี import/module จริง —
ดู `DEPENDENCY_MAP.md`) เพิ่มฟังก์ชันใหม่ `exportIssuesToSheet()` ไว้ไฟล์
เดียวกันนี้ด้วย (pattern เดียวกับสองตัวเดิม)

**ยืนยันแล้ว** (2026-07-29, เห็นโค้ดจริงจาก `TestDrive.js` แล้ว): signature
ทั้งสองฟังก์ชันตรงกับที่ร่างไว้ในหัวข้อ 5 ทุกจุด — `exportCrossCheckToSheet`
มี helper ภายในชื่อ `writeTab()` (clear-if-exists-else-insert แล้วเขียน
header+data) ซึ่งเป็น logic เดียวกับที่ `exportElementsToSheet` เขียนแบบ
inline ตรงๆ — **ตัดสินใจแล้ว: รวมเป็น helper กลางตัวเดียว `writeTab_()`**
ใช้ร่วมกันทั้ง 3 ฟังก์ชัน (พฤติกรรมเดิมทุกจุด แค่ไม่ซ้ำโค้ด) — ดูโค้ดเต็มที่
อัปเดตแล้วในหัวข้อ 6

---

## 4. ไฟล์ที่จะสร้าง/แก้/ย้าย

| ไฟล์ | การเปลี่ยนแปลง |
|---|---|
| `reference/gsheet/GS_Pipeline.gs` (ใหม่) | `normalizePiLabels_(rows)` + `runFullPipeline(fileId, tabName)` — orchestrator หลักของปุ่มคำนวณ |
| `reference/gsheet/GS_SheetExport.gs` (ใหม่) | ย้าย `exportElementsToSheet()`/`exportCrossCheckToSheet()` จาก `TestDrive.js` มาไว้ที่นี่ (เนื้อโค้ดเดิม) + เพิ่ม `exportIssuesToSheet()` ใหม่ |
| `TestDrive.js` (แก้ — ลบเฉพาะ 2 ฟังก์ชันที่ย้ายออก) | ฟังก์ชัน test เดิมที่เรียกใช้ (`testFullPipelineExportAgainstHorOrr04`, `testFullCrossCheckAgainstHorOrr04`) ไม่ต้องแก้ ยังเรียกได้ปกติ |
| `reference/gsheet/Index.html` (แก้) | ผูก `calcBtn.onclick`, disable/enable ระหว่างรัน, แสดงสรุปผล/error |

ไม่แตะ: `GS_TableSplitter.gs`, `GS_PiTableParser.gs`, `GS_AlignmentBuilder.gs`,
`GS_ElementTable.gs`, `GS_CrossCheck.gs`, `GS_DriveWalker.gs` (ทุกไฟล์ engine
เดิมคงเดิมหมด)

---

## 5. `GS_Pipeline.gs` — รายละเอียด

```javascript
// แปลง label "PI1".."PI99" (ไม่มีขีด) เป็น "PI-1".."PI-99" ก่อนเข้า splitter
// ไม่แตะแถวที่มีขีดอยู่แล้ว (PI-5) หรือ BP/EP/blank — ปรับเฉพาะคอลัมน์ POINT
function normalizePiLabels_(rows) {
  var header = rows[0];
  var pointCol = -1;
  for (var i = 0; i < header.length; i++) {
    if (String(header[i]).trim().toLowerCase() === 'point') { pointCol = i; break; }
  }
  if (pointCol === -1) return rows; // ไม่มีคอลัมน์ POINT ปล่อยผ่าน ให้ splitter จัดการ error เอง

  var out = [header];
  for (var r = 1; r < rows.length; r++) {
    var row = rows[r].slice(); // copy กันแก้ของเดิม
    var cell = String(row[pointCol]).trim();
    var m = /^PI(\d+)$/.exec(cell);
    if (m) row[pointCol] = 'PI-' + m[1];
    out.push(row);
  }
  return out;
}

function runFullPipeline(fileId, tabName) {
  var ss = SpreadsheetApp.openById(fileId);
  var sheet = ss.getSheetByName(tabName);
  if (!sheet) throw new Error('ไม่พบ tab "' + tabName + '" ในไฟล์นี้');

  var rows = normalizePiLabels_(sheet.getDataRange().getValues());
  var split = GS_TableSplitter.splitMixedAlignmentTable(rows);
  var vertices = GS_PiTableParser.parsePiTable(split.vertexRows);
  var built = GS_AlignmentBuilder.buildFromPI(vertices);

  exportElementsToSheet(ss, tabName, built.elements);
  exportCrossCheckToSheet(ss, tabName, built.elements, split.drawing, rows, vertices, built.control);
  exportIssuesToSheet(ss, tabName, built.issues);

  return {
    elementsCount: built.elements.length,
    issuesCount: built.issues.length
  };
}
```

---

## 6. `GS_SheetExport.gs` — รายละเอียด (ยืนยันแล้ว, รวม helper กลาง)

ย้าย `exportElementsToSheet`/`exportCrossCheckToSheet` จาก `TestDrive.js`
มาไว้ที่นี่ พร้อมรวม `writeTab()`/logic การเขียน inline เดิมเป็น helper กลาง
`writeTab_()` ตัวเดียว (พฤติกรรมเดิมทุกจุด ไม่เปลี่ยน) แล้วเพิ่ม
`exportIssuesToSheet()` ใหม่บน helper เดียวกัน:

```javascript
function writeTab_(ss, name, header, dataRows) {
  var sh = ss.getSheetByName(name);
  if (sh) {
    sh.clear();
  } else {
    sh = ss.insertSheet(name);
  }
  var data = [header].concat(dataRows);
  sh.getRange(1, 1, data.length, header.length).setValues(data);
}

function exportElementsToSheet(ss, alignmentName, elements) {
  var rows = GS_ElementTable.elementsToRows(elements);
  writeTab_(ss, 'result_' + alignmentName + '_Elements', GS_ElementTable.HEADER, rows);
}

function exportCrossCheckToSheet(ss, alignmentName, elements, drawing, rows, vertices, control) {
  var pointsResults = GS_CrossCheck.checkPoints(elements, drawing);
  writeTab_(ss, 'result_' + alignmentName + '_CrossCheck_Points', GS_CrossCheck.POINTS_HEADER, GS_CrossCheck.pointsToRows(pointsResults));

  var piChecks = GS_CrossCheck.checkPiCurves(rows, vertices, control);
  writeTab_(ss, 'result_' + alignmentName + '_CrossCheck_Radius', GS_CrossCheck.RADIUS_HEADER, GS_CrossCheck.radiusToRows(piChecks));
  writeTab_(ss, 'result_' + alignmentName + '_CrossCheck_Deflection', GS_CrossCheck.DEFLECTION_HEADER, GS_CrossCheck.deflectionToRows(piChecks));
}

// ต่างจากอีก 2 ฟังก์ชัน: ไม่สร้าง tab ใหม่ถ้า issues ว่างเปล่า (กันรก) —
// แต่ถ้า tab เก่ามีอยู่จาก run ก่อนหน้า (ตอนนั้นมี issues) ต้องเคลียร์ทิ้ง
// กันข้อมูลเก่าค้างหลอกผู้ใช้
function exportIssuesToSheet(ss, alignmentName, issues) {
  var name = 'result_' + alignmentName + '_Issues';
  if (!issues || issues.length === 0) {
    var sh = ss.getSheetByName(name);
    if (sh) sh.clear();
    return;
  }
  var rows = issues.map(function (msg) { return [msg]; });
  writeTab_(ss, name, ['Issue'], rows);
}
```

`TestDrive.js` เดิม: ลบเฉพาะ definition ของ `exportElementsToSheet`/
`exportCrossCheckToSheet` ออก — `testFullPipelineExportAgainstHorOrr04()`/
`testFullCrossCheckAgainstHorOrr04()` เรียกใช้ชื่อฟังก์ชันเดิมได้ปกติ ไม่ต้อง
แก้อะไร (global scope เดียวกันทั้งโปรเจกต์)

---

## 7. `Index.html` — ส่วนที่แก้

- `calcBtn` เดิม disabled ถาวร → เปลี่ยนเป็น enabled ปกติ (ผูก onclick)
- เพิ่ม `<div id="calcStatus">` สำหรับข้อความสถานะ/สรุปผล
- `calcBtn.onclick`:
  1. อ่าน `fileSelect.value` (fileId), `tabSelect.value` (tabName)
  2. disable `catSelect`, `fileSelect`, `tabSelect`, `calcBtn`
  3. `calcStatus.textContent = 'กำลังคำนวณ...'`
  4. `google.script.run.withSuccessHandler(onCalcDone).withFailureHandler(onCalcFail).runFullPipeline(fileId, tabName)`
- `onCalcDone(summary)`:
  1. re-enable dropdown ทั้ง 3 + ปุ่ม
  2. `calcStatus.textContent = 'คำนวณเสร็จแล้ว: ' + summary.elementsCount + ' elements' + (summary.issuesCount ? ', พบ issues ' + summary.issuesCount + ' รายการ' : ', ไม่พบ issues')`
- `onCalcFail(err)`:
  1. re-enable dropdown ทั้ง 3 + ปุ่ม
  2. เรียก `showError(err)` (ฟังก์ชันเดิมจาก F.3 — ใช้ของเดิม ไม่เพิ่มใหม่)

---

## 8. Error handling

ใช้ `showError()`/`errorBanner` เดิมจาก F.3 ทั้งหมด ไม่ต้องเพิ่มกลไกใหม่ —
server-side throw (เช่น tab หาไม่เจอ, ข้อมูลผิดรูปแบบจน `parsePiTable`/
`buildFromPI` throw) จะเด้งเข้า `withFailureHandler` อัตโนมัติ

---

## 9. การทดสอบ

- `normalizePiLabels_()` เป็น logic ใหม่ล้วนๆ (ไม่มี Python oracle เพราะเป็น
  เรื่อง GAS/Sheet-input เท่านั้น) — แนะนำ Node smoke test เล็กๆ ก่อน (ไม่กี่
  เคส: `PI1`→`PI-1`, `PI-1` ไม่เปลี่ยน, `BP`/`EP` ไม่เปลี่ยน, `PI` ตามด้วย
  ตัวอักษรไม่ใช่ตัวเลขไม่เปลี่ยน)
- `runFullPipeline()` เป็น orchestration ล้วนๆ (ไม่มี logic ใหม่ นอกจาก
  normalize) — verify ผ่าน Test deployments เหมือน F.3 (ไม่มี oracle ให้ diff)

Checklist ทดสอบจริงผ่านเบราว์เซอร์:

1. คำนวณ `001_Hor_Align`/`HOR-ORR-04` (ข้อมูลถูกต้อง ไม่มี issues) — เช็ค 4
   tab ผลลัพธ์ถูกต้อง + ไม่มี tab Issues (หรือถ้ามีจาก run เก่า ต้องว่างเปล่า)
   + สรุปผลบนหน้าเว็บถูกต้อง
2. อัปโหลด `SettingOutTest_Part_2.csv` เป็น tab ใหม่ (label ไม่มีขีด) คำนวณ —
   เช็คว่า normalizer ทำงาน ไม่ error, ผลลัพธ์ถูกต้อง
3. กดคำนวณซ้ำ 2 ครั้งติด — เช็คว่าทับผลเดิมได้ไม่มีปัญหา
4. dropdown ทั้ง 3 + ปุ่ม disable ระหว่างรันจริง (ดูด้วยตา)

---

## 10. ขอบเขตที่ไม่ทำใน F.4

- ไม่ deploy production จริง (F.5)
- ไม่ backport normalizer ไป Python (ทำทีหลังตามที่คุยไว้)
- ไม่แก้ `split_mixed_alignment_table()`/`GS_TableSplitter.gs` หรือฟังก์ชัน
  อื่นที่ "ห้ามแก้"
