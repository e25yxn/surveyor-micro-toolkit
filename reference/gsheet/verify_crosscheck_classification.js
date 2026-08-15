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
