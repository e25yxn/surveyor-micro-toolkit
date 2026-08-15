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
