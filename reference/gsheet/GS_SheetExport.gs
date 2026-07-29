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
