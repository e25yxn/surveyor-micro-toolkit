# PLAN — Sync .gs classification logic to match Python (drawing-point whitelist) — FINALIZED, verified
**วันที่:** 2026-08-15
**สำหรับ:** Claude Code — apply diff ตรงๆ ได้เลย (ผ่านการทดสอบจริงแล้วในรอบนี้)
**ขอบเขต: ฝั่ง `.gs` เท่านั้น** — Python ปิดจ็อบและ push แล้ว (`d9a5d9d`) เป็น commit แยกก่อนหน้านี้
**สถานะ:** ✅ implement + test ผ่าน Node แล้วใน sandbox ของ Claude Chat ครบทุกไฟล์

---

## 1) เหตุผล — ทำไมต้อง sync

Python (`table_splitter.py`) เปลี่ยนจาก vertex-pattern regex เป็น drawing-point whitelist ไปแล้ว (commit `d9a5d9d`) เพราะ regex เดิม (`^(BP|PI-\d+|EP)$`) ไม่รองรับ label convention จริงในโปรเจกต์ (bare "PI", "IP1"/"IP2") — ฝั่ง `.gs` ยังใช้ regex เดิมอยู่ ถ้าไม่ sync จะกลายเป็นปัญหาแบบเดียวกับที่ Session #5 เจอมาก่อน (Python กับ `.gs` เบี่ยงกัน) แม้ตอนนี้จะยังไม่กระทบข้อมูลจริงบนเว็บแอป (HOR-ORR-04 ใช้ "PI-n" อยู่แล้ว) แต่เป็นการป้องกันไว้ล่วงหน้า

## 2) พบจุดที่สาม — ไม่ใช่แค่ `GS_TableSplitter.gs`

นอกจาก `GS_TableSplitter.gs` (ตัวหลัก mirror ของ Python) ยังพบว่า **`GS_CrossCheck.gs` มี logic การจำแนกแบบเดียวกันซ้ำอยู่อีกชุดหนึ่ง** (`scanRawRows_()` ฟังก์ชันภายใน) — ตั้งใจแยกโค้ดออกจาก `GS_TableSplitter.gs` (ตามคอมเมนต์ในไฟล์: "Mirrors แผนแม่ §2.4 ทางเลือก (ก) — ไม่แก้ GS_TableSplitter.gs") เพื่อเดินตามลำดับแถวดิบ (ก่อน split) สำหรับ Table 2b/2c (CrossCheck_Radius/Deflection) **ไม่มี Python oracle เทียบเลย** (comment ในไฟล์ยืนยัน: "logic ใหม่ทั้งหมด — ไม่มี Python function ให้ diff=0 ตรงๆ") — ปลอดภัยแก้ตรงได้ แต่ **ถ้าแก้แค่ `GS_TableSplitter.gs` โดยไม่แก้จุดนี้ด้วย จะกลายเป็นสองระบบจำแนกไม่ตรงกันเองในโปรเจกต์เดียวกัน** (ตรงข้ามกับเป้าหมายของงานนี้)

`checkPiCurves()` มี safety assertion ในตัวอยู่แล้ว (`vertexRowCount !== vertices.length` → throw) ที่จะจับความไม่ตรงกันนี้ได้ — แต่ดีกว่าที่จะไม่ให้เกิดตั้งแต่แรก

## 3) วิธีที่ใช้จริง — เหมือน Python เป๊ะ (verified ผ่าน Node)

```javascript
// เดิม (ทั้ง 2 ไฟล์):
var VERTEX_POINT_RE = /^(BP|PI-\d+|EP)$/;
// ...
if (!point || VERTEX_POINT_RE.test(point)) { /* vertex */ }

// ใหม่:
var DRAWING_POINT_RE = /^(PT|PC|PCC|TS|SC|CS|ST)$/;
// ...
if (!point || !DRAWING_POINT_RE.test(point)) { /* vertex */ }
```

## 4) ทดสอบยืนยันครบผ่าน Node (raw output จริง)

**ยืนยันว่า GS_PiTableParser.gs รองรับ label ทุกแบบอยู่แล้ว** (ไม่ special-case อะไรนอกจาก BP/EP — ตรงกับ Python) เช็คโค้ดแล้วมีแค่ `point === 'BP'` และ `point === 'EP'` เท่านั้น ไม่มี pattern check อื่น — ปลอดภัยที่จะใช้ inverted logic

**`verify_drawing_point_whitelist.js` (16 checks, ไฟล์ใหม่):**
```
--- 1) AL1_test_alignment_PI.csv (bare PI + IP1/IP2) ---
PASS  AL1 vertexRows count (incl header)  value=16
PASS  AL1 drawing count  value=0
PASS  AL1 max element-field diff (direct vs split-routed)  diff=0.000e+0

--- 2) HOR_01N01.csv (mixed table, PI-n + IP-1 + PCC/PT/PC) ---
PASS  HOR_01N01 vertex labels match Python  value=["BP","PI-1","PI-2","PI-3","PI-4","PI-5","IP-1","EP"]
PASS  HOR_01N01 drawing labels match Python  value=["PCC","PT","PC","PCC","PT","PC","PT"]
PASS  HOR_01N01 built element count  value=12

--- 3) HOR_ORR_04.csv (existing golden fixture, must be unaffected) ---
PASS  HOR_ORR_04 vertexRows count (incl header)  value=14
PASS  HOR_ORR_04 drawing count  value=22

=== 16 passed, 0 failed ===
```
**ทุกตัวเลขตรงกับผลที่ Python ยืนยันไว้แล้วเป๊ะ** (16/0, 8 vertex labels, 7 drawing labels, 14/22)

**`verify_crosscheck_classification.js` (4 checks, ไฟล์ใหม่ — ทดสอบ `checkPiCurves()` จริงบนข้อมูลจริง):**
```
--- 1) HOR_ORR_04.csv - checkPiCurves() end-to-end, real production data ---
PASS  HOR_ORR_04 checkPiCurves() runs without throwing  (no throw)
PASS  HOR_ORR_04 checkPiCurves() produced at least one row  value=true

--- 2) HOR_01N01.csv - scanRawRows_ vs GS_TableSplitter agreement (has IP-1) ---
PASS  HOR_01N01 vertices.length (via GS_TableSplitter) is 8, incl IP-1  value=8
PASS  HOR_01N01 checkPiCurves() no longer throws the vertexRowCount mismatch error  (no throw)

=== 4 passed, 0 failed ===
```

**เทส control (ก่อนแก้ ยืนยันว่าปัญหาเดิมมีจริง):** `git stash` กลับไปโค้ดเดิมชั่วคราว รัน `GS_TableSplitter` บน `HOR_01N01.csv` — ได้ vertex แค่ 7 (ขาด IP-1 ไป 1 จุด) เทียบกับ 8 หลังแก้ — ยืนยันว่า bug มีจริงและ fix แก้ได้ตรงจุด

**เทสเดิมที่มีอยู่แล้วไม่พัง:** `smoke_test.js` (23/23), `test_error_message_map.js` (8/8) — ไม่กระทบทั้งคู่

---

## 5) การเปลี่ยนแปลงจริง (verified diff — 2 ไฟล์)

```diff
diff --git a/reference/gsheet/GS_CrossCheck.gs b/reference/gsheet/GS_CrossCheck.gs
index 0e64b73..f46be06 100644
--- a/reference/gsheet/GS_CrossCheck.gs
+++ b/reference/gsheet/GS_CrossCheck.gs
@@ -96,7 +96,7 @@ var GS_CrossCheck = (function () {
   // original interleaved row order (BP, PI-1, PT, PC, PI-2, ...) is preserved.
   // Mirrors แผนแม่ §2.4 ทางเลือก (ก) — ไม่แก้ GS_TableSplitter.gs
   // ==========================================================================
-  var VERTEX_POINT_RE = /^(BP|PI-\d+|EP)$/;
+  var DRAWING_POINT_RE = /^(PT|PC|PCC|TS|SC|CS|ST)$/;
 
   // header cell (lowercased) -> canonical column key (subset needed here)
   var COL_ALIASES_ = {
@@ -163,7 +163,7 @@ var GS_CrossCheck = (function () {
         e: toNumber_(cell_(row, colMap, 'easting')),
         sta: staRaw ? toNumber_(staRaw) : null
       };
-      if (VERTEX_POINT_RE.test(name)) {
+      if (!DRAWING_POINT_RE.test(name)) {
         rec.kind = 'vertex';
         rec.vertexIndex = vidx;
         vidx++;
@@ -248,7 +248,7 @@ var GS_CrossCheck = (function () {
     // นับ ตรงกับตำแหน่งจริงใน vertices[] ที่ parsePiTable() สร้าง — เช็คแบบง่าย
     // ที่สุดที่ยืนยันได้โดยไม่ต้อง re-parse: จำนวนแถวที่ scanRawRows_ ติด
     // kind='vertex' ต้องเท่ากับ vertices.length เป๊ะ (ถ้าไม่เท่า แปลว่า regex
-    // VERTEX_POINT_RE หรือกติกานับแถว sub ที่นี่เพี้ยนไปจาก parsePiTable จริง)
+    // DRAWING_POINT_RE หรือกติกานับแถว sub ที่นี่เพี้ยนไปจาก parsePiTable จริง)
     var vertexRowCount = 0;
     for (var k = 0; k < recs.length; k++) {
       if (recs[k].kind === 'vertex') vertexRowCount++;
@@ -257,7 +257,7 @@ var GS_CrossCheck = (function () {
       throw new Error(
         'GS_CrossCheck.checkPiCurves: scanRawRows_ นับแถว vertex ได้ ' + vertexRowCount +
         ' แถว แต่ vertices.length = ' + vertices.length + ' — vertexIndex จะจับคู่กับ ' +
-        'vertices[] ผิดตำแหน่ง (ตรวจ VERTEX_POINT_RE หรือการนับแถว compound sub-row)'
+        'vertices[] ผิดตำแหน่ง (ตรวจ DRAWING_POINT_RE หรือการนับแถว compound sub-row)'
       );
     }
 
diff --git a/reference/gsheet/GS_TableSplitter.gs b/reference/gsheet/GS_TableSplitter.gs
index 3a60d8d..a120700 100644
--- a/reference/gsheet/GS_TableSplitter.gs
+++ b/reference/gsheet/GS_TableSplitter.gs
@@ -19,7 +19,7 @@
 var GS_TableSplitter = (function () {
   'use strict';
 
-  var VERTEX_POINT_RE = /^(BP|PI-\d+|EP)$/;
+  var DRAWING_POINT_RE = /^(PT|PC|PCC|TS|SC|CS|ST)$/;
 
   // header cell (lowercased) -> canonical column key
   // mirrors the subset of table_splitter._COL_ALIASES this module needs
@@ -85,7 +85,7 @@ var GS_TableSplitter = (function () {
       if (isBlankRow_(row)) continue;
 
       var point = cell_(row, colMap, 'point');
-      if (!point || VERTEX_POINT_RE.test(point)) {
+      if (!point || !DRAWING_POINT_RE.test(point)) {
         var cleaned = row.slice();
         for (var k = 0; k < NUMERIC_KEYS.length; k++) {
           var key = NUMERIC_KEYS[k];
```

## 6) ไฟล์เทสใหม่ (permanent — เหมือน `smoke_test.js`/`test_error_message_map.js` ที่มีอยู่แล้ว)

### `reference/gsheet/verify_drawing_point_whitelist.js`
```javascript
/**
 * Node verification for GS_TableSplitter.gs's inverted classification fix
 * (2026-08-15, mirrors the Python fix already committed as d9a5d9d).
 *
 * Cross-checks against the same real fixtures used to verify the Python
 * side, and against the exact numbers already confirmed there.
 *
 * Run: node reference/gsheet/verify_drawing_point_whitelist.js
 */
'use strict';

var fs = require('fs');
var path = require('path');

var GS_TableSplitter = require('./GS_TableSplitter.gs');
var GS_PiTableParser  = require('./GS_PiTableParser.gs');
var GS_AlignmentBuilder = require('./GS_AlignmentBuilder.gs');

var passCount = 0;
var failures = [];

function assertEqual(actual, expected, label) {
  if (JSON.stringify(actual) === JSON.stringify(expected)) {
    passCount++;
    console.log('PASS  ' + label + '  value=' + JSON.stringify(actual));
  } else {
    failures.push(label + ': actual=' + JSON.stringify(actual) + ' expected=' + JSON.stringify(expected));
    console.log('FAIL  ' + label + '  actual=' + JSON.stringify(actual) + '  expected=' + JSON.stringify(expected));
  }
}

function assertClose(actual, expected, tol, label) {
  var diff = Math.abs(actual - expected);
  if (diff <= tol) {
    passCount++;
    console.log('PASS  ' + label + '  diff=' + diff.toExponential(3));
  } else {
    failures.push(label + ': actual=' + actual + ' expected=' + expected + ' diff=' + diff);
    console.log('FAIL  ' + label + '  actual=' + actual + '  expected=' + expected + '  diff=' + diff);
  }
}

// Minimal CSV parser that respects quoted commas (matches Python's csv.reader
// behaviour for the thousands-separator-quoted cells in these fixtures).
function parseCsv(text) {
  var rows = [];
  var lines = text.replace(/\r\n/g, '\n').split('\n');
  for (var li = 0; li < lines.length; li++) {
    var line = lines[li];
    if (line === '') continue;
    var row = [];
    var cur = '';
    var inQuotes = false;
    for (var i = 0; i < line.length; i++) {
      var c = line[i];
      if (c === '"') { inQuotes = !inQuotes; continue; }
      if (c === ',' && !inQuotes) { row.push(cur); cur = ''; continue; }
      cur += c;
    }
    row.push(cur);
    rows.push(row);
  }
  return rows;
}

var DATA = path.join(__dirname, '..', '..', 'test_data');

// ---------------------------------------------------------------------
// 1) AL1_test_alignment_PI.csv - bare "PI" + IP1/IP2, byte-identical-
//    geometry check same as the Python verification.
// ---------------------------------------------------------------------
console.log('\n--- 1) AL1_test_alignment_PI.csv (bare PI + IP1/IP2) ---');
var al1Rows = parseCsv(fs.readFileSync(path.join(DATA, 'AL1_test_alignment_PI.csv'), 'utf8'));

var al1Split = GS_TableSplitter.splitMixedAlignmentTable(al1Rows);
assertEqual(al1Split.vertexRows.length, 16, 'AL1 vertexRows count (incl header)');
assertEqual(al1Split.drawing.length, 0, 'AL1 drawing count');
var al1Labels = al1Split.vertexRows.slice(1).map(function (r) { return r[0]; });
assertEqual(al1Labels[1], 'IP1', 'AL1 vertex[1] label is IP1');
assertEqual(al1Labels[2], 'IP2', 'AL1 vertex[2] label is IP2');

var al1VerticesDirect = GS_PiTableParser.parsePiTable(al1Rows);
var al1BuiltDirect     = GS_AlignmentBuilder.buildFromPI(al1VerticesDirect);
var al1VerticesSplit   = GS_PiTableParser.parsePiTable(al1Split.vertexRows);
var al1BuiltSplit       = GS_AlignmentBuilder.buildFromPI(al1VerticesSplit);

assertEqual(al1BuiltDirect.elements.length, al1BuiltSplit.elements.length, 'AL1 element count matches (direct vs split-routed)');
assertEqual(al1BuiltDirect.issues, al1BuiltSplit.issues, 'AL1 issues match (direct vs split-routed)');

var maxDiff = 0;
for (var i = 0; i < al1BuiltDirect.elements.length; i++) {
  var ed = al1BuiltDirect.elements[i];
  var es = al1BuiltSplit.elements[i];
  maxDiff = Math.max(maxDiff, Math.abs(ed.staStart - es.staStart), Math.abs(ed.staEnd - es.staEnd),
                      Math.abs(ed.n - es.n), Math.abs(ed.e - es.e));
}
assertClose(maxDiff, 0.0, 1e-9, 'AL1 max element-field diff (direct vs split-routed)');

// ---------------------------------------------------------------------
// 2) HOR_01N01.csv - mixed table, PI-1..PI-5 + IP-1 + PCC/PT/PC
//    Cross-checked against Python's confirmed numbers: 8 vertices incl
//    IP-1, 7 drawing points, 12 built elements, no issues.
// ---------------------------------------------------------------------
console.log('\n--- 2) HOR_01N01.csv (mixed table, PI-n + IP-1 + PCC/PT/PC) ---');
var horRows = parseCsv(fs.readFileSync(path.join(DATA, 'HOR_01N01.csv'), 'utf8'));
var horSplit = GS_TableSplitter.splitMixedAlignmentTable(horRows);
var horVertexLabels = horSplit.vertexRows.slice(1).map(function (r) { return r[0]; });
var horDrawingLabels = horSplit.drawing.map(function (d) { return d.name; });

assertEqual(horVertexLabels, ['BP', 'PI-1', 'PI-2', 'PI-3', 'PI-4', 'PI-5', 'IP-1', 'EP'], 'HOR_01N01 vertex labels match Python');
assertEqual(horDrawingLabels, ['PCC', 'PT', 'PC', 'PCC', 'PT', 'PC', 'PT'], 'HOR_01N01 drawing labels match Python');

var horVertices = GS_PiTableParser.parsePiTable(horSplit.vertexRows);
var horBuilt = GS_AlignmentBuilder.buildFromPI(horVertices);
assertEqual(horVertices.length, 8, 'HOR_01N01 parsed vertex count');
assertEqual(horBuilt.elements.length, 12, 'HOR_01N01 built element count');
assertEqual(horBuilt.issues.length, 0, 'HOR_01N01 no issues');

// ---------------------------------------------------------------------
// 3) HOR_ORR_04.csv - existing golden fixture (already covered by
//    tests/builders/test_table_splitter.py's TestSplit class); same
//    counts must still hold after the classification change.
// ---------------------------------------------------------------------
console.log('\n--- 3) HOR_ORR_04.csv (existing golden fixture, must be unaffected) ---');
var orrRows = parseCsv(fs.readFileSync(path.join(DATA, 'HOR_ORR_04.csv'), 'utf8'));
var orrSplit = GS_TableSplitter.splitMixedAlignmentTable(orrRows);
assertEqual(orrSplit.vertexRows.length, 14, 'HOR_ORR_04 vertexRows count (incl header)');
assertEqual(orrSplit.drawing.length, 22, 'HOR_ORR_04 drawing count');

var orrVertices = GS_PiTableParser.parsePiTable(orrSplit.vertexRows);
var orrBuilt = GS_AlignmentBuilder.buildFromPI(orrVertices);
assertEqual(orrVertices.length, 13, 'HOR_ORR_04 parsed vertex count');
assertEqual(orrBuilt.issues.length, 0, 'HOR_ORR_04 no issues');

// ---------------------------------------------------------------------
console.log('\n=== ' + passCount + ' passed, ' + failures.length + ' failed ===');
if (failures.length > 0) {
  console.log('\nFAILURES:');
  failures.forEach(function (f) { console.log('  ' + f); });
  process.exit(1);
}
process.exit(0);
```

### `reference/gsheet/verify_crosscheck_classification.js`
```javascript
/**
 * Node verification that GS_CrossCheck.gs's independent scanRawRows_
 * classification (2026-08-15 fix) now agrees with GS_TableSplitter.gs's,
 * and that checkPiCurves() still runs correctly end-to-end on the real
 * production fixture (HOR_ORR_04.csv) and no longer trips the
 * vertexRowCount safety assertion on a table with IP-n vertices
 * (HOR_01N01.csv).
 *
 * Run: node reference/gsheet/verify_crosscheck_classification.js
 */
'use strict';

var fs = require('fs');
var path = require('path');

var GS_TableSplitter    = require('./GS_TableSplitter.gs');
var GS_PiTableParser    = require('./GS_PiTableParser.gs');
var GS_AlignmentBuilder = require('./GS_AlignmentBuilder.gs');
var GS_CrossCheck       = require('./GS_CrossCheck.gs');

var passCount = 0;
var failures = [];

function assertEqual(actual, expected, label) {
  if (JSON.stringify(actual) === JSON.stringify(expected)) {
    passCount++;
    console.log('PASS  ' + label + '  value=' + JSON.stringify(actual));
  } else {
    failures.push(label + ': actual=' + JSON.stringify(actual) + ' expected=' + JSON.stringify(expected));
    console.log('FAIL  ' + label + '  actual=' + JSON.stringify(actual) + '  expected=' + JSON.stringify(expected));
  }
}

function assertNoThrow(fn, label) {
  try {
    var result = fn();
    passCount++;
    console.log('PASS  ' + label + '  (no throw)');
    return result;
  } catch (e) {
    failures.push(label + ': threw ' + e.message);
    console.log('FAIL  ' + label + '  threw: ' + e.message);
    return null;
  }
}

function parseCsv(text) {
  var rows = [];
  var lines = text.replace(/\r\n/g, '\n').split('\n');
  for (var li = 0; li < lines.length; li++) {
    var line = lines[li];
    if (line === '') continue;
    var row = [];
    var cur = '';
    var inQuotes = false;
    for (var i = 0; i < line.length; i++) {
      var c = line[i];
      if (c === '"') { inQuotes = !inQuotes; continue; }
      if (c === ',' && !inQuotes) { row.push(cur); cur = ''; continue; }
      cur += c;
    }
    row.push(cur);
    rows.push(row);
  }
  return rows;
}

var DATA = path.join(__dirname, '..', '..', 'test_data');

// ---------------------------------------------------------------------
// 1) HOR_ORR_04.csv - the one real production dataset (HOR-ORR-04 on the
//    live webapp). checkPiCurves() must still run cleanly, same as before
//    this fix (no IP-labels in this file, so behaviour should be
//    unchanged - this proves no regression on real data).
// ---------------------------------------------------------------------
console.log('\n--- 1) HOR_ORR_04.csv - checkPiCurves() end-to-end, real production data ---');
var orrRows = parseCsv(fs.readFileSync(path.join(DATA, 'HOR_ORR_04.csv'), 'utf8'));
var orrSplit = GS_TableSplitter.splitMixedAlignmentTable(orrRows);
var orrVertices = GS_PiTableParser.parsePiTable(orrSplit.vertexRows);
var orrBuilt = GS_AlignmentBuilder.buildFromPI(orrVertices);

var orrRadiusRows = assertNoThrow(function () {
  return GS_CrossCheck.checkPiCurves(orrRows, orrVertices, orrBuilt.control);
}, 'HOR_ORR_04 checkPiCurves() runs without throwing');

if (orrRadiusRows) {
  assertEqual(orrRadiusRows.length > 0, true, 'HOR_ORR_04 checkPiCurves() produced at least one row');
}

// ---------------------------------------------------------------------
// 2) HOR_01N01.csv - has a real IP-1 vertex. Before this fix,
//    scanRawRows_ (old VERTEX_POINT_RE) and GS_TableSplitter (already
//    fixed) would have disagreed on whether IP-1 is a vertex, tripping
//    checkPiCurves()'s own vertexRowCount === vertices.length safety
//    assertion. Must run clean now that both use the same
//    DRAWING_POINT_RE logic.
// ---------------------------------------------------------------------
console.log('\n--- 2) HOR_01N01.csv - scanRawRows_ vs GS_TableSplitter agreement (has IP-1) ---');
var horRows = parseCsv(fs.readFileSync(path.join(DATA, 'HOR_01N01.csv'), 'utf8'));
var horSplit = GS_TableSplitter.splitMixedAlignmentTable(horRows);
var horVertices = GS_PiTableParser.parsePiTable(horSplit.vertexRows);
var horBuilt = GS_AlignmentBuilder.buildFromPI(horVertices);

assertEqual(horVertices.length, 8, 'HOR_01N01 vertices.length (via GS_TableSplitter) is 8, incl IP-1');

assertNoThrow(function () {
  return GS_CrossCheck.checkPiCurves(horRows, horVertices, horBuilt.control);
}, 'HOR_01N01 checkPiCurves() no longer throws the vertexRowCount mismatch error');

// ---------------------------------------------------------------------
console.log('\n=== ' + passCount + ' passed, ' + failures.length + ' failed ===');
if (failures.length > 0) {
  console.log('\nFAILURES:');
  failures.forEach(function (f) { console.log('  ' + f); });
  process.exit(1);
}
process.exit(0);
```

---

## 7) ขั้นตอนสำหรับ Claude Code

1. Apply diff ในหัวข้อ 5 ตรงตามที่ระบุ (2 ไฟล์: `GS_TableSplitter.gs`, `GS_CrossCheck.gs`)
2. สร้างไฟล์เทสใหม่ 2 ไฟล์ตามหัวข้อ 6 เป๊ะๆ (เนื้อหา verified แล้ว)
3. รันทั้ง 4 test script ยืนยัน raw output:
```
node reference/gsheet/verify_drawing_point_whitelist.js
node reference/gsheet/verify_crosscheck_classification.js
node reference/gsheet/smoke_test.js
node reference/gsheet/test_error_message_map.js
```
ทั้ง 4 ต้อง exit code 0 — ส่ง raw output มาให้ดู (คาดว่า 16/16, 4/4, 23/23, 8/8 ตามลำดับ)
4. `git diff --stat` ต้องเห็น 2 ไฟล์แก้ + 2 ไฟล์ใหม่ (untracked) เท่านั้น
5. Commit message ผ่าน heredoc (`cat >` เขียนทับ) แล้ว `wc -l -w -c` เช็คก่อน commit เสมอ (ข้อความยาว):

```
fix(gsheet): sync drawing-point-whitelist classification from Python

Mirrors the Python fix (commit d9a5d9d): GS_TableSplitter.gs's old
vertex-pattern regex (BP|PI-\d+|EP) doesn't match the project's real
data conventions - AL1_test_alignment_PI.csv uses a bare repeated
"PI" label plus real angle-point vertices "IP1"/"IP2", which no
PI-pattern regex would catch without missing at least one convention.

Inverted the classification: whitelist the finite, well-known set of
drawing control-point abbreviations (PT/PC/PCC/TS/SC/CS/ST) and treat
everything else non-blank as a vertex - matching GS_PiTableParser.gs's
own actual behaviour (only 'BP'/'EP' special-cased, confirmed by
reading its source, no other pattern check exists).

Also found and fixed the same VERTEX_POINT_RE pattern independently
duplicated in GS_CrossCheck.gs's scanRawRows_() - a raw-row walker
for Table 2b/2c (CrossCheck_Radius/Deflection, GAS-only extension
logic with no Python oracle). Left unfixed, this would have
classified the same row differently than GS_TableSplitter.gs,
silently working against checkPiCurves()'s own vertexRowCount
safety assertion. Confirmed via git-stash control test that
HOR_01N01.csv (which has a real IP-1 vertex) previously produced
only 7 vertices instead of 8 through the old regex.

Verified via 2 new permanent Node test scripts (matching the existing
smoke_test.js/test_error_message_map.js pattern), cross-checked
against the exact numbers already confirmed on the Python side:
AL1_test_alignment_PI.csv byte-identical geometry (0.000000000000 m
max diff, direct vs split-routed path), HOR_01N01.csv correct 8/7
vertex/drawing split including IP-1, HOR_ORR_04.csv unaffected
(14/22, matches the pre-existing golden fixture). checkPiCurves()
runs end-to-end on both HOR_ORR_04.csv (real production data) and
HOR_01N01.csv without throwing. Existing smoke_test.js (23/23) and
test_error_message_map.js (8/8) unaffected.

Not yet deployed - clasp push to the live webapp (D:\MyClasp_SMT_DEMO)
is a separate, deliberate next step, same pattern as Session #5.
```

6. `git add` เฉพาะไฟล์ที่เกี่ยวข้อง:
```
git add reference/gsheet/GS_TableSplitter.gs reference/gsheet/GS_CrossCheck.gs reference/gsheet/verify_drawing_point_whitelist.js reference/gsheet/verify_crosscheck_classification.js
git status --short
```
7. `git commit -F .git/smt_commit_msg.txt` → `git log -3 --oneline` ยืนยัน local → `git push`
8. Append `session_logs/latest.md` ผ่าน `cat >>` heredoc เท่านั้น (ห้าม Update/Edit tool)

---

## 8) ขั้นตอนต่อไป — แยกจาก commit นี้ (CK1024 ทำเอง ไม่ใช่ Claude Code)

**Deploy จริง (ตาม pattern Session #5):**
1. `cd D:\MyClasp_SMT_DEMO`
2. `clasp status` เช็คก่อนเสมอ
3. **เทียบ `appsscript.json` กับ Apps Script online editor ก่อน force push ทุกครั้ง** (กฎ 3.7 เดิม — เคยเกือบทับ deployment config ทิ้งมาแล้ว)
4. `clasp push -f`
5. Live-test ผ่าน Test deployment ในเบราว์เซอร์ (ทดสอบ HOR-ORR-04 ที่มีอยู่จริง ต้องได้ผลเดิมทุกประการ — ไม่มี IP-label ในไฟล์นี้อยู่แล้วจึงไม่ควรมีอะไรเปลี่ยน)
