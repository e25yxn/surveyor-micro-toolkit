/**
 * GS_PiTableParser — mirrors Python src/smt/builders/alignment_builder.py::parse_pi_table()
 * (commit 4b76841, lines 219-328)
 *
 * ============================================================================
 *  แปลงตาราง PI (แถวแรก = header) เป็น vertex list สำหรับป้อนต่อ
 *  GS_AlignmentBuilder.buildFromPI() — เทียบเท่า parse_pi_table() ทุกประการ
 * ----------------------------------------------------------------------------
 *  คอลัมน์ (จับคู่แบบไม่สนตัวพิมพ์ใหญ่เล็กจาก header row):
 *    POINT / (เดียวกัน)      — 'BP' | 'EP' | ป้าย PI | ว่าง = compound sub-row
 *    N / NORTHING            — northing
 *    E / EASTING             — easting
 *    STA / CHAINAGE          — chainage เริ่มต้น (เฉพาะ BP; default 0.0)
 *    R / RADIUS              — รัศมีเมตร; ว่างหรือ '0' = angle point (EXT-001)
 *    LS / SPIRAL             — ความยาว spiral สมมาตร
 *    LSIN                    — ความยาว spiral ขาเข้า (ทับ LS เมื่อไม่ว่าง)
 *    LSOUT                   — ความยาว spiral ขาออก (ทับ LS เมื่อไม่ว่าง)
 *    TRANS / TRANSITION      — CLOTHOID (default) | BLOSS | COSINE | SINE
 *    DELTA                   — มุมเบี่ยงองศา (compound sub-row; ว่างบนโค้งสุดท้าย)
 *
 *  คอลัมน์ที่ไม่มีใน header ใช้ default (STA -> 0.0; อื่นๆ -> ว่าง)
 *  แถว POINT ว่างที่มี R ไม่ว่าง = compound sub-arc ผูกกับ PI ก่อนหน้า
 *  แถว POINT ว่างที่ R ว่างด้วย = แถวว่าง ข้ามไป
 *
 *  Throw Error เมื่อเซลล์ตัวเลขผิดรูป (mirror float() ValueError ของ Python —
 *  ใช้ Number() แทน parseFloat() เพราะ parseFloat() แกะเลขนำหน้าแล้วเงียบทิ้ง
 *  ขยะต่อท้าย เช่น parseFloat("12abc")===12 ซึ่ง Python float("12abc") จะ raise)
 *
 *  Throw Error เมื่อ PI มีทั้ง RADIUS ตรงๆ และ compound sub-row ตามมา
 *  — ข้อความเป็นภาษาไทยชุดเดียวกับ Python เป๊ะ (เลือกคงข้อความเดิมไว้ ไม่แปล
 *  เป็นอังกฤษ เพื่อให้ error message ตรงกันทั้งสอง engine เวลาเทียบผลลัพธ์)
 *
 *  หมายเหตุยืนยันจาก Session B: parse_pi_table() ฝั่ง Python ไม่มี column
 *  alias สำหรับ TRANSIN/TRANSOUT (มีแค่ TRANS/TRANSITION) — โมดูลนี้จึงไม่
 *  รองรับเช่นกัน (ตั้งใจ mirror ให้ตรงเป๊ะ ไม่ใช่ตกหล่น) GS_AlignmentBuilder.
 *  buildFromPI จะ fallback ไปที่ .trans เองอยู่แล้วเมื่อ vertex ไม่มี
 *  transIn/transOut — ดู reference/gsheet/GS_AlignmentBuilder.gs:82-83
 *
 *  ไม่มี dependency ภายนอก (pure string/object reshaping เหมือน GS_TableSplitter)
 * ============================================================================
 */
var GS_PiTableParser = (function () {
  'use strict';

  // header cell (lowercased) -> canonical column key
  // mirrors Python's _COL_ALIASES (src/smt/builders/alignment_builder.py:181-198) ทุกตัว
  var COL_ALIASES = {
    'point':      'point',
    'n':          'northing',
    'northing':   'northing',
    'e':          'easting',
    'easting':    'easting',
    'sta':        'sta',
    'chainage':   'sta',
    'r':          'radius',
    'radius':     'radius',
    'ls':         'ls',
    'spiral':     'ls',
    'lsin':       'lsin',
    'lsout':      'lsout',
    'trans':      'trans',
    'transition': 'trans',
    'delta':      'delta'
  };

  function parseHeader_(headerRow) {
    var colMap = {};
    for (var i = 0; i < headerRow.length; i++) {
      var key = COL_ALIASES[String(headerRow[i]).trim().toLowerCase()];
      if (key !== undefined && colMap[key] === undefined) colMap[key] = i;
    }
    return colMap;
  }

  function cell_(row, colMap, key) {
    var idx = colMap[key];
    if (idx === undefined || idx >= row.length) return '';
    return String(row[idx]).trim();
  }

  // mirror Python float(): raise on blank/non-numeric cells instead of the
  // silent lenient parse that parseFloat() would do.
  function toFloat_(str) {
    var s = String(str).trim();
    if (s === '' || isNaN(Number(s))) {
      throw new Error('invalid numeric cell: "' + s + '"');
    }
    return Number(s);
  }

  // mirrors parse_pi_table() (src/smt/builders/alignment_builder.py:219-328) line-for-line.
  function parsePiTable(rows) {
    var colMap = parseHeader_(rows[0]);

    function g(row, key) { return cell_(row, colMap, key); }

    var vertices = [];
    var pendingPi = null;
    var pendingPiLabel = '';
    var pendingPiLine = 0;
    var compoundArcs = [];
    var compoundArcsFirstLine = 0;

    function flushPending_() {
      if (pendingPi === null) {
        // FIX (Oracle correction, session_logs/review_src_smt_20260802.md #3,
        // session_logs/plan_<TBD>.md): mirrors parse_pi_table's
        // _flush_pending (src/smt/builders/alignment_builder.py, commit
        // 795f36b) line-for-line. A compound sub-row with no PI to attach
        // to (before the first PI, or after EP) used to leak silently onto
        // the next PI or vanish at EOF -- now raises instead.
        if (compoundArcs.length) {
          throw new Error(
            'compound sub-row (แถวที่ ' + compoundArcsFirstLine + ') มีค่า RADIUS ' +
            'แต่ไม่มี PI ก่อนหน้าให้ผูก (อยู่ก่อน PI ตัวแรก ก่อน BP, ' +
            'หรืออยู่หลัง EP) ' +
            'ตรวจสอบลำดับแถวในไฟล์ว่าไม่มีแถวตกหล่นหรือเรียงผิดที่'
          );
        }
        return;
      }
      var v;
      if (compoundArcs.length) {
        if (pendingPi.R !== undefined) {
          throw new Error(
            'PI "' + pendingPiLabel + '" (แถวที่ ' + pendingPiLine + ') มีทั้งค่า RADIUS ' +
            '(' + pendingPi.R + ') และมี compound sub-row ตามมา ' +
            'กำกวมว่าจะใช้ค่ารัศมีไหน ' +
            'ให้ปล่อย RADIUS ของแถว PI นี้ว่างไว้ ' +
            'แล้วย้ายค่า RADIUS (และ Delta ถ้ามี) ' +
            'ไปเป็นแถว compound sub-row แยกต่างหากแทน'
          );
        }
        v = { n: pendingPi.n, e: pendingPi.e, compound: compoundArcs.slice() };
        compoundArcs = [];
      } else {
        v = Object.assign({}, pendingPi);
      }
      vertices.push(v);
      pendingPi = null;
    }

    for (var r = 1; r < rows.length; r++) {   // r=1: rows[0] is the header
      var lineNo = r + 1;                     // +1: mirrors Python enumerate(rows[1:], start=2)
      var row = rows[r];
      var point = g(row, 'point');

      if (!point) {
        // compound sub-row — only meaningful when R is non-blank
        var rRaw = g(row, 'radius');
        if (!rRaw) continue;
        if (!compoundArcs.length) compoundArcsFirstLine = lineNo;
        var arc = { R: toFloat_(rRaw) };
        var deltaRaw = g(row, 'delta');
        if (deltaRaw) arc.delta = toFloat_(deltaRaw);
        compoundArcs.push(arc);
        continue;
      }

      flushPending_();

      var n = toFloat_(g(row, 'northing'));
      var e = toFloat_(g(row, 'easting'));

      if (point === 'BP') {
        var staRaw = g(row, 'sta');
        vertices.push({ n: n, e: e, sta: staRaw ? toFloat_(staRaw) : 0.0 });
        continue;
      }

      if (point === 'EP') {
        vertices.push({ n: n, e: e });
        continue;
      }

      // PI vertex
      var piDict = { n: n, e: e };
      var rRaw2 = g(row, 'radius');
      if (rRaw2 && toFloat_(rRaw2) !== 0.0) {
        piDict.R = toFloat_(rRaw2);
        var lsRaw = g(row, 'ls');
        var lsinRaw = g(row, 'lsin');
        var lsoutRaw = g(row, 'lsout');
        if (lsinRaw || lsoutRaw) {
          if (lsinRaw) piDict.LsIn = toFloat_(lsinRaw);
          if (lsoutRaw) piDict.LsOut = toFloat_(lsoutRaw);
        } else if (lsRaw) {
          piDict.Ls = toFloat_(lsRaw);
        }
        var trans = g(row, 'trans');
        if (trans) piDict.trans = trans;
      }
      // else: R absent or 0 -> angle point (ไม่มี key R); อาจได้ 'compound' ทีหลัง

      pendingPi = piDict;
      pendingPiLabel = point;
      pendingPiLine = lineNo;
    }

    flushPending_();
    return vertices;
  }

  return { parsePiTable: parsePiTable };
})();

if (typeof module !== 'undefined' && module.exports) module.exports = GS_PiTableParser;
