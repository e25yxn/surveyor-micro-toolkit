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
