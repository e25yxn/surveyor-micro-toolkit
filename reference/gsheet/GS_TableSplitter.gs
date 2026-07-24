/**
 * GS_TableSplitter — mirrors Python src/smt/builders/table_splitter.py (commit 7abd919)
 *
 * ============================================================================
 *  แยกตารางดิบที่มี BP/PI-n/PT/PC/TS/SC/CS/ST/EP ปนกันแถวเดียวกัน (เช่น
 *  test_data/HOR_ORR_04.csv) ออกเป็น 2 ชุด:
 *    - vertexRows : เฉพาะแถว BP, PI-n, EP (+ compound sub-row ที่ POINT ว่าง)
 *                   ป้อนต่อ parse_pi_table()-เทียบเท่า / GS_AlignmentBuilder.buildFromPI ได้ตรง ๆ
 *    - drawing    : เฉพาะแถวจุดที่เหลือ (PT/PC/TS/SC/CS/ST) เป็น {name,sta,n,e}
 *                   ป้อนต่อ GS_AlignmentBuilder.crossCheck ได้ตรง ๆ
 *
 *  ตัวเลขในคอลัมน์ sta/northing/easting/radius/ls/lsin/lsout/delta จะถูกตัด
 *  thousands-separator comma ออกก่อน (เช่น "1,537,772.85" -> "1537772.85")
 *  ไม่แก้ตรรกะ parse/build/check เดิมใด ๆ — โมดูลนี้คือ adapter เท่านั้น
 *
 *  ไม่มี dependency ภายนอก (pure string/object reshaping)
 * ============================================================================
 */
var GS_TableSplitter = (function () {
  'use strict';

  var VERTEX_POINT_RE = /^(BP|PI-\d+|EP)$/;

  // header cell (lowercased) -> canonical column key
  // mirrors the subset of table_splitter._COL_ALIASES this module needs
  var COL_ALIASES = {
    'point':      'point',
    'sta':        'sta',
    'chainage':   'sta',
    'n':          'northing',
    'northing':   'northing',
    'e':          'easting',
    'easting':    'easting',
    'r':          'radius',
    'radius':     'radius',
    'ls':         'ls',
    'spiral':     'ls',
    'lsin':       'lsin',
    'lsout':      'lsout',
    'delta':      'delta',
    'trans':      'trans',
    'transition': 'trans'
  };

  // columns that may carry thousands-separator commas in quoted CSV cells
  var NUMERIC_KEYS = ['sta', 'northing', 'easting', 'radius', 'ls', 'lsin', 'lsout', 'delta'];

  function parseHeader_(headerRow) {
    var colMap = {};
    for (var i = 0; i < headerRow.length; i++) {
      var key = COL_ALIASES[String(headerRow[i]).trim().toLowerCase()];
      if (key !== undefined && colMap[key] === undefined) colMap[key] = i;
    }
    return colMap;
  }

  function stripThousandsSeparators_(value) {
    return String(value).split(',').join('');
  }

  function cell_(row, colMap, key) {
    var idx = colMap[key];
    if (idx === undefined || idx >= row.length) return '';
    return String(row[idx]).trim();
  }

  function isBlankRow_(row) {
    if (!row || row.length === 0) return true;
    for (var i = 0; i < row.length; i++) {
      if (String(row[i]).trim() !== '') return false;
    }
    return true;
  }

  // แยก rows (array-of-array, rows[0]=header) -> {vertexRows, drawing}
  function splitMixedAlignmentTable(rows) {
    var header = rows[0];
    var colMap = parseHeader_(header);
    var vertexRows = [header];
    var drawing = [];

    for (var r = 1; r < rows.length; r++) {
      var row = rows[r];
      if (isBlankRow_(row)) continue;

      var point = cell_(row, colMap, 'point');
      if (!point || VERTEX_POINT_RE.test(point)) {
        var cleaned = row.slice();
        for (var k = 0; k < NUMERIC_KEYS.length; k++) {
          var key = NUMERIC_KEYS[k];
          var idx = colMap[key];
          if (idx !== undefined && idx < cleaned.length) {
            cleaned[idx] = stripThousandsSeparators_(String(cleaned[idx]).trim());
          }
        }
        vertexRows.push(cleaned);
      } else {
        drawing.push({
          name: point,
          sta: parseFloat(stripThousandsSeparators_(cell_(row, colMap, 'sta'))),
          n:   parseFloat(stripThousandsSeparators_(cell_(row, colMap, 'northing'))),
          e:   parseFloat(stripThousandsSeparators_(cell_(row, colMap, 'easting')))
        });
      }
    }

    return { vertexRows: vertexRows, drawing: drawing };
  }

  return { splitMixedAlignmentTable: splitMixedAlignmentTable };
})();

if (typeof module !== 'undefined' && module.exports) module.exports = GS_TableSplitter;
