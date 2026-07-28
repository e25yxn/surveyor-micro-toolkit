function listCategoryFolders() {
  var SMT_WEB_APP_ROOT_FOLDER_ID = "12GFHdG6RJMbnRmtFRyFH6uVXjJeZm1-p"; // SMT_Web_App_demo root (ยืนยันแล้วจาก testExploreFolders เดิม)
  var root = DriveApp.getFolderById(SMT_WEB_APP_ROOT_FOLDER_ID);
  var subfolders = root.getFolders();
  var result = [];
  while (subfolders.hasNext()) {
    var f = subfolders.next();
    result.push({id: f.getId(), name: f.getName()});
  }
  result.sort(function(a, b) { return a.name.localeCompare(b.name); });
  return result;
}

function listFilesInFolder(folderId) {
  var folder = DriveApp.getFolderById(folderId);
  var files = folder.getFilesByType(MimeType.GOOGLE_SHEETS);
  var result = [];
  while (files.hasNext()) {
    var f = files.next();
    result.push({id: f.getId(), name: f.getName()});
  }
  result.sort(function(a, b) { return a.name.localeCompare(b.name); });
  return result;
}

function listAlignmentTabsInFile(fileId) {
  var ss = SpreadsheetApp.openById(fileId);
  var sheets = ss.getSheets();
  var knownResultHeaders = [
    GS_ElementTable.HEADER,
    GS_CrossCheck.POINTS_HEADER,
    GS_CrossCheck.RADIUS_HEADER,
    GS_CrossCheck.DEFLECTION_HEADER
  ];

  function headerMatches(a, b) {
    if (a.length !== b.length) return false;
    for (var i = 0; i < a.length; i++) {
      if (a[i] !== b[i]) return false;
    }
    return true;
  }

  var result = [];
  sheets.forEach(function(sh) {
    var name = sh.getName();
    if (name.indexOf("result_") === 0) return;

    var lastCol = sh.getLastColumn();
    if (lastCol > 0) {
      var header = sh.getRange(1, 1, 1, lastCol).getValues()[0];
      for (var k = 0; k < knownResultHeaders.length; k++) {
        if (headerMatches(header, knownResultHeaders[k])) return;
      }
    }
    result.push(name);
  });
  result.sort(function(a, b) { return a.localeCompare(b); });
  return result;
}
