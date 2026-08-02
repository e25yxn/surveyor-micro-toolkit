/**
 * Node regression test for ERROR_MESSAGE_MAP / getFriendlyMessage() in Index.html
 * -----------------------------------------------------------------------
 * Per session_logs/plan_20260802_1107.md (F.6.3) — extracts the REAL
 * ERROR_MESSAGE_MAP array + getFriendlyMessage() function straight out of
 * Index.html (never retyped by hand, avoids drift between test and source)
 * and asserts the raw->friendly mapping for both prefixed and unprefixed
 * rawMessage inputs.
 *
 * Why this exists: F.6.2 verified getFriendlyMessage() with raw messages
 * that had NO prefix (matches calling .gs functions directly via Node).
 * The real deployed app goes through google.script.run, which prepends an
 * error-class prefix (e.g. "Error: ") to err.message before it reaches the
 * client — so the F.6.2 tests passed while the real banner still fell
 * through to the catchall. This file tests BOTH forms every time so that
 * class of regression cannot silently reappear.
 *
 * Run:  node reference/gsheet/test_error_message_map.js
 * Exit code 0 = all checks passed; non-zero = at least one failure.
 */
'use strict';

var fs = require('fs');
var path = require('path');

var htmlPath = path.join(__dirname, 'Index.html');
var html = fs.readFileSync(htmlPath, 'utf8');

// Regexes anchored to the REAL 4-space indentation used inside <script> in
// Index.html (verified by hand against the file before writing this test —
// a naive "\n}" with no indent, as first drafted, does NOT exist in the
// file and silently fails to match).
var mapMatch = /var ERROR_MESSAGE_MAP = \[[\s\S]*?\n    \];/.exec(html);
var fnMatch = /function getFriendlyMessage\(rawMessage\) \{[\s\S]*?\n    \}/.exec(html);

if (!mapMatch) {
  console.log('FAIL  could not extract ERROR_MESSAGE_MAP from Index.html — regex out of sync with file');
  process.exit(1);
}
if (!fnMatch) {
  console.log('FAIL  could not extract getFriendlyMessage() from Index.html — regex out of sync with file');
  process.exit(1);
}

var src = mapMatch[0] + '\n' + fnMatch[0] +
  '\nmodule.exports = { ERROR_MESSAGE_MAP: ERROR_MESSAGE_MAP, getFriendlyMessage: getFriendlyMessage };';

var mod = { exports: {} };
new Function('module', src)(mod);

var ERROR_MESSAGE_MAP = mod.exports.ERROR_MESSAGE_MAP;
var getFriendlyMessage = mod.exports.getFriendlyMessage;

var passCount = 0;
var failures = [];

function assertStartsWith(label, rawMessage, expectPrefix) {
  var actual = getFriendlyMessage(rawMessage);
  if (actual.indexOf(expectPrefix) === 0) {
    passCount++;
    console.log('PASS  ' + label);
  } else {
    failures.push(label + ': expected friendly message to start with "' + expectPrefix +
      '" but got "' + actual + '" (rawMessage=' + JSON.stringify(rawMessage) + ')');
    console.log('FAIL  ' + label);
  }
}

console.log('--- sanity: ERROR_MESSAGE_MAP shape ---');
if (ERROR_MESSAGE_MAP.length === 7) {
  passCount++;
  console.log('PASS  ERROR_MESSAGE_MAP has 7 entries');
} else {
  failures.push('ERROR_MESSAGE_MAP.length: expected 7, got ' + ERROR_MESSAGE_MAP.length);
  console.log('FAIL  ERROR_MESSAGE_MAP has 7 entries (got ' + ERROR_MESSAGE_MAP.length + ')');
}

console.log('\n--- raw->friendly mapping (table from plan_20260802_1107.md) ---');

assertStartsWith(
  '1 tab-not-found, prefixed',
  'Error: ไม่พบ tab "Test_Sheet" ในไฟล์นี้',
  'ไม่พบแท็บ (tab) ชื่อ'
);

assertStartsWith(
  '2 alignment incomplete, prefixed (the real bug case found in F.6.3 live testing)',
  'Error: ไม่พบข้อมูล alignment ที่ครบถ้วนในตารางนี้ — ต้องมีอย่างน้อยจุดเริ่ม (BP) และจุดจบ (EP) กรุณาตรวจสอบว่ากรอกข้อมูลครบหรือไม่',
  'ชีต/แท็บนี้ยังไม่มีข้อมูล alignment ครบถ้วน'
);

assertStartsWith(
  '3 alignment incomplete, no prefix (backward compat with direct/Node-style calls)',
  'ไม่พบข้อมูล alignment ที่ครบถ้วนในตารางนี้ — ต้องมีอย่างน้อยจุดเริ่ม (BP) และจุดจบ (EP) กรุณาตรวจสอบว่ากรอกข้อมูลครบหรือไม่',
  'ชีต/แท็บนี้ยังไม่มีข้อมูล alignment ครบถ้วน'
);

assertStartsWith(
  '4 invalid numeric cell, prefixed (embedded colon must not confuse the strip)',
  'Error: invalid numeric cell: "12,000"',
  'พบข้อมูลตัวเลขที่อ่านไม่ได้ในตาราง ("12,000")'
);

assertStartsWith(
  '5 PI compound sub-row conflict, prefixed',
  'Error: PI "PI7" (แถวที่ 12) มีรัศมีซ้ำกับ compound sub-row',
  'ข้อมูลขัดแย้งกันที่ PI7 (แถวที่ 12 ในตาราง)'
);

assertStartsWith(
  '6 non-anchored pattern (station outside alignment), prefixed — regression check',
  'Error: station 123.45 อยู่นอกแนวเส้นทาง',
  'จุดตรวจสอบบางจุดอยู่นอกช่วงแนวเส้นทาง'
);

assertStartsWith(
  '7 unmatched message, prefixed, falls through to catchall',
  'Error: อะไรก็ไม่รู้ที่ไม่ตรง pattern ไหนเลย',
  'เกิดข้อผิดพลาดที่ไม่ทราบสาเหตุแน่ชัด'
);

console.log('\n============================================================');
console.log(passCount + ' passed, ' + failures.length + ' failed');
if (failures.length > 0) {
  console.log('\nFAILURES:');
  failures.forEach(function (f) { console.log('  - ' + f); });
  process.exit(1);
} else {
  console.log('ALL ERROR_MESSAGE_MAP TESTS PASSED');
  process.exit(0);
}
