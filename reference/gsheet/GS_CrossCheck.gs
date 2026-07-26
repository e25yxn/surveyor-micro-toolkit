/**
 * GS_CrossCheck — Session E: three drawing-vs-design cross-check tables.
 *
 * ============================================================================
 *  Approved design: session_logs/plan_20260726_1558.md (ยืนยันแล้ว 2026-07-26)
 *  แผนแม่: session_logs/HANDOFF_SMT_SESSION_E_PLAN_20260725.md §2-3
 * ----------------------------------------------------------------------------
 *  ตาราง 2a — CrossCheck_Points   : mirrors src/smt/check.py::check_horizontal()
 *                                    (มี oracle ตรงตัว, ไม่ใช่ logic ใหม่)
 *  ตาราง 2b — CrossCheck_Radius   : logic ใหม่ทั้งหมด — ไม่มี Python function
 *                                    ให้ diff=0 ตรงๆ (verify ผ่าน prototype +
 *                                    hand-check แทน ดูแผนที่อนุมัติ §1, §6)
 *  ตาราง 2c — CrossCheck_Deflection: logic ใหม่ทั้งหมด เช่นเดียวกับ 2b
 *
 *  การตัดสินใจที่อนุมัติแล้ว (แผน §0, §2, §3):
 *    - หน่วย ΔDeflection: องศา (ทศนิยม) + คอลัมน์ฟิลิปดา (arcsec) เพิ่มอีกคอลัมน์
 *    - PI angle-point (ไม่มี R) และ PI ที่มี spiral/compound: skip ออกจากตาราง
 *      2b/2c ทั้งคู่ (ไม่มีรัศมี/deflection ออกแบบเดี่ยวให้เทียบ)
 *    - Δ_drawn คำนวณจาก azimuth(PC→PI) และ azimuth(PI→PT) โดยตรง (ไม่ใช่มุม
 *      ระหว่างเวกเตอร์ PI→PC กับ PI→PT ตามตัวอักษรแผนแม่ ซึ่งจะได้ 180°−Δ ผิด)
 *    - ΔRadius ใช้ |R_calc| − |R_design| (ไม่ใช่ค่าที่มีเครื่องหมายตรงๆ เพราะ
 *      buildFromPI ไม่สนใจเครื่องหมาย R ในตารางอยู่แล้ว — ดู
 *      GS_AlignmentBuilder.gs บรรทัด curveSubs_ที่ทำ Math.abs(vert.R) เสมอ)
 *      พร้อมคอลัมน์ SignOK แยกต่างหากเพื่อจับเครื่องหมายผิดโดยไม่ทำให้ตัวเลข
 *      ΔRadius เกินจริง
 *    - EP-substitution (เฉพาะกรณีไม่มีแถว PT แยกในตารางดิบ): ใช้พิกัด EP แทน
 *      ได้ก็ต่อเมื่อ PT ที่ buildFromPI คำนวณได้จริงอยู่ใกล้ EP ภายใน snap
 *      tolerance เท่านั้น (ยืนยันด้วย engine จริงแล้วสำหรับ PI-11 ในชุดข้อมูล
 *      ทดสอบ — ไม่ใช่การเดา ดูแผนที่อนุมัติ §3.1)
 *
 *  EXTENSION: beyond oracle — ตาราง 2b/2c ไม่มีเทียบเท่าใน reference/*.gs เดิม
 *  (oracle เดิมมีแค่ crossCheck() ของ GS_AlignmentBuilder.gs ซึ่งเทียบเท่า
 *  ตาราง 2a เท่านั้น)
 *
 *  สร้างบน FPMath, WCB, GS_Alignment (ใช้ public API เท่านั้น ไม่แก้ไฟล์เดิม)
 *  รับ elements/vertices/control/drawing/rows เป็น argument จากภายนอกทั้งหมด
 *  (เหมือน pattern ของ GS_ElementTable.gs) — ไม่ import GS_TableSplitter,
 *  GS_PiTableParser, GS_AlignmentBuilder โดยตรง เพื่อลด coupling
 * ============================================================================
 */
if (typeof FPMath === 'undefined' && typeof require !== 'undefined')       { var FPMath = require('../FPMath.gs'); }
if (typeof WCB === 'undefined' && typeof require !== 'undefined')          { var WCB = require('../WCB.gs'); }
if (typeof GS_Alignment === 'undefined' && typeof require !== 'undefined') { var GS_Alignment = require('./GS_Alignment.gs'); }

var GS_CrossCheck = (function () {
  'use strict';

  var SNAP_TOL = 0.01;   // metres; mirrors check.py::_snap_to_alignment_ends

  // ==========================================================================
  // Table 2a — CrossCheck_Points (mirrors check.py::check_horizontal())
  // ==========================================================================
  var POINTS_HEADER = ['Name', 'STA', 'dN', 'dE', 'Gap', 'OK'];

  // mirrors check.py::_snap_to_alignment_ends
  function snapToAlignmentEnds_(sta, elements, snap) {
    if (snap === undefined) snap = SNAP_TOL;
    var start = elements[0].staStart;
    var end = elements[elements.length - 1].staEnd;
    if (sta < start && (start - sta) <= snap) return start;
    if (sta > end && (sta - end) <= snap) return end;
    return sta;
  }

  // mirrors check.py::check_horizontal()
  function checkPoints(elements, drawing, tol) {
    if (tol === undefined) tol = 0.05;
    var results = [];
    for (var i = 0; i < drawing.length; i++) {
      var d = drawing[i];
      var staEff = snapToAlignmentEnds_(d.sta, elements, SNAP_TOL);
      var calc = GS_Alignment.stationToCoord(elements, staEff, 0.0);
      var deltaN = calc.n - d.n;
      var deltaE = calc.e - d.e;
      var gap = Math.hypot(deltaN, deltaE);
      results.push({
        name: d.name, sta: d.sta,
        deltaN: deltaN, deltaE: deltaE, gap: gap,
        ok: gap <= tol
      });
    }
    return results;
  }

  function pointsToRows(results) {
    var rows = [];
    for (var i = 0; i < results.length; i++) {
      var r = results[i];
      rows.push([r.name, r.sta, r.deltaN, r.deltaE, r.gap, r.ok]);
    }
    return rows;
  }

  // ==========================================================================
  // PI <-> PC/PT neighbour matching from the RAW table (pre-split), so the
  // original interleaved row order (BP, PI-1, PT, PC, PI-2, ...) is preserved.
  // Mirrors แผนแม่ §2.4 ทางเลือก (ก) — ไม่แก้ GS_TableSplitter.gs
  // ==========================================================================
  var VERTEX_POINT_RE = /^(BP|PI-\d+|EP)$/;

  // header cell (lowercased) -> canonical column key (subset needed here)
  var COL_ALIASES_ = {
    'point':    'point',
    'sta':      'sta',
    'chainage': 'sta',
    'n':        'northing',
    'northing': 'northing',
    'e':        'easting',
    'easting':  'easting'
  };

  function parseHeader_(headerRow) {
    var colMap = {};
    for (var i = 0; i < headerRow.length; i++) {
      var key = COL_ALIASES_[String(headerRow[i]).trim().toLowerCase()];
      if (key !== undefined && colMap[key] === undefined) colMap[key] = i;
    }
    return colMap;
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

  function stripThousandsSeparators_(value) {
    return String(value).split(',').join('');
  }

  function toNumber_(str) {
    return parseFloat(stripThousandsSeparators_(str));
  }

  // เดินตาม rows ดิบ (ก่อน split) ติด kind ให้ทุกแถวที่ไม่ว่าง ตามลำดับเดิม:
  //   {kind:'vertex'|'drawing'|'sub', name, n, e, sta, vertexIndex}
  // vertexIndex ตรงกับตำแหน่งใน vertices[] ที่ parsePiTable() จะสร้าง
  // (แถว sub ที่ POINT ว่าง ไม่กิน index — ตรงกับพฤติกรรม parsePiTable)
  function scanRawRows_(rows) {
    var colMap = parseHeader_(rows[0]);
    var out = [];
    var vidx = 0;
    for (var r = 1; r < rows.length; r++) {
      var row = rows[r];
      if (isBlankRow_(row)) continue;
      var name = cell_(row, colMap, 'point');
      if (!name) {
        out.push({ kind: 'sub', name: '', vertexIndex: null });
        continue;
      }
      var staRaw = cell_(row, colMap, 'sta');
      var rec = {
        name: name,
        n: toNumber_(cell_(row, colMap, 'northing')),
        e: toNumber_(cell_(row, colMap, 'easting')),
        sta: staRaw ? toNumber_(staRaw) : null
      };
      if (VERTEX_POINT_RE.test(name)) {
        rec.kind = 'vertex';
        rec.vertexIndex = vidx;
        vidx++;
      } else {
        rec.kind = 'drawing';
        rec.vertexIndex = null;
      }
      out.push(rec);
    }
    return out;
  }

  // เพื่อนบ้านตัวแรกที่ไม่ใช่ 'sub' ในทิศ step จาก i — คืนค่าเฉพาะเมื่อเป็นแถว
  // drawing ที่ชื่อ === want เท่านั้น ไม่งั้นคืน null
  function neighbourDrawingPoint_(recs, i, step, want) {
    var j = i + step;
    while (j >= 0 && j < recs.length && recs[j].kind === 'sub') j += step;
    if (j < 0 || j >= recs.length) return null;
    var rec = recs[j];
    return (rec.kind === 'drawing' && rec.name === want) ? rec : null;
  }

  // เหมือนข้างบนแต่ไม่สนใจ kind (ใช้เฉพาะเช็คเพื่อนบ้านชื่อ 'EP' สำหรับกฎ
  // EP-substitution เท่านั้น — EP เป็นแถว vertex ไม่ใช่ drawing)
  function neighbourAnyPoint_(recs, i, step, want) {
    var j = i + step;
    while (j >= 0 && j < recs.length && recs[j].kind === 'sub') j += step;
    if (j < 0 || j >= recs.length) return null;
    var rec = recs[j];
    return (rec.name === want) ? rec : null;
  }

  // ==========================================================================
  // engine-computed PT lookup — ใช้เฉพาะเป็น guard ของกฎ EP-substitution
  // (ไม่ใช่แหล่งข้อมูลหลักของ T_out/Δ_drawn — นั่นยังคงมาจากพิกัดที่ "ตามแบบจริง"
  // เสมอ ตามเจตนาเดิมของแผนแม่ที่ต้องการเทียบ design กับ as-drawn อย่างอิสระ)
  // ==========================================================================
  var END_NAMES_ = { PT: true, ST: true, IP: true };

  // แบ่ง control[1:-1] (ตัด BP/EP ทิ้ง) เป็นกลุ่มละ 1 PI ตามลำดับ vertex
  // แต่ละกลุ่ม = [จุดเริ่ม, ..., จุดจบ] โดยจุดจบชื่ออยู่ใน END_NAMES_
  // mirrors GS_AlignmentBuilder.gs::names_()/curveSubs_() ที่สร้าง control list
  function splitControlIntoPiGroups_(control) {
    var groups = [], cur = [];
    for (var i = 1; i < control.length - 1; i++) {
      var c = control[i];
      cur.push(c);
      if (END_NAMES_[c.name]) { groups.push(cur); cur = []; }
    }
    return groups;
  }

  // PT ที่ engine คำนวณได้จริงสำหรับ vertices[v] (เฉพาะโค้งธรรมดา กลุ่ม =
  // [PC, PT] พอดี) — คืน null ถ้าไม่ใช่โค้งธรรมดา (จุดจบไม่ใช่ 'PT')
  function enginePtForVertex_(control, v) {
    var groups = splitControlIntoPiGroups_(control);
    var group = groups[v - 1];
    var end = group[group.length - 1];
    return (end.name === 'PT') ? end : null;
  }

  // ==========================================================================
  // Table 2b/2c — logic ใหม่ (ไม่มี oracle ให้ mirror)
  // ==========================================================================
  var RADIUS_HEADER = [
    'Name', 'R design', 'T_in', 'T_out', 'R from T_in', 'R from T_out',
    'dR (T_in)', 'dR (T_out)', 'SignOK', 'Note'
  ];
  var DEFLECTION_HEADER = [
    'Name', 'Deflection design (deg)', 'Deflection drawn (deg)',
    'dDeflection (deg)', 'dDeflection (sec)'
  ];

  // สร้าง payload สำหรับตาราง 2b/2c — หนึ่งเรคคอร์ดต่อ PI โค้งธรรมดา 1 จุด
  //   rows     : ตารางดิบ (pre-split), rows[0] = header
  //   vertices : ผลจาก parsePiTable(splitMixedAlignmentTable(rows).vertexRows)
  //   control  : buildFromPI(vertices).control
  function checkPiCurves(rows, vertices, control) {
    var recs = scanRawRows_(rows);

    // แผนที่อนุมัติ §7 ความเสี่ยงข้อ 3: ต้องแน่ใจว่า vertexIndex ที่ scanRawRows_
    // นับ ตรงกับตำแหน่งจริงใน vertices[] ที่ parsePiTable() สร้าง — เช็คแบบง่าย
    // ที่สุดที่ยืนยันได้โดยไม่ต้อง re-parse: จำนวนแถวที่ scanRawRows_ ติด
    // kind='vertex' ต้องเท่ากับ vertices.length เป๊ะ (ถ้าไม่เท่า แปลว่า regex
    // VERTEX_POINT_RE หรือกติกานับแถว sub ที่นี่เพี้ยนไปจาก parsePiTable จริง)
    var vertexRowCount = 0;
    for (var k = 0; k < recs.length; k++) {
      if (recs[k].kind === 'vertex') vertexRowCount++;
    }
    if (vertexRowCount !== vertices.length) {
      throw new Error(
        'GS_CrossCheck.checkPiCurves: scanRawRows_ นับแถว vertex ได้ ' + vertexRowCount +
        ' แถว แต่ vertices.length = ' + vertices.length + ' — vertexIndex จะจับคู่กับ ' +
        'vertices[] ผิดตำแหน่ง (ตรวจ VERTEX_POINT_RE หรือการนับแถว compound sub-row)'
      );
    }

    var out = [];

    for (var i = 0; i < recs.length; i++) {
      var rec = recs[i];
      if (rec.kind !== 'vertex' || rec.name.indexOf('PI-') !== 0) continue;

      var v = rec.vertexIndex;
      var vert = vertices[v];

      // eligibility (แผนแม่ §2.3 คำตอบที่ 2 + แผนที่อนุมัติ §0)
      if (vert.compound) continue;                          // compound: นอกขอบเขต
      if (vert.Ls || vert.LsIn || vert.LsOut) continue;      // spiral: ไม่มี R/T เดี่ยว
      var rDesign = vert.R;
      if (!rDesign) continue;                                // angle point: ไม่มีอะไรให้เทียบ

      // design deflection — คำนวณซ้ำเองจากพิกัด PI ล้วนๆ ไม่แตะ
      // GS_AlignmentBuilder.gs / buildFromPI เลย (แผนแม่ §2.3(7))
      var prevV = vertices[v - 1], nextV = vertices[v + 1];
      var azInDesign  = WCB.azimuthFromCoords(prevV.n, prevV.e, vert.n, vert.e);
      var azOutDesign = WCB.azimuthFromCoords(vert.n, vert.e, nextV.n, nextV.e);
      var deltaDesign = FPMath.angleDiff(azOutDesign, azInDesign);

      // as-drawn PC / PT จากตารางดิบ
      var pc = neighbourDrawingPoint_(recs, i, -1, 'PC');
      var pt = neighbourDrawingPoint_(recs, i, +1, 'PT');
      var note = '';

      // EP-substitution (แผนที่อนุมัติ §3.1, §5): ใช้ได้เฉพาะเมื่อ PT ที่
      // engine คำนวณได้จริงอยู่ใกล้ EP ภายใน SNAP_TOL เท่านั้น
      if (!pt) {
        var epNeighbour = neighbourAnyPoint_(recs, i, +1, 'EP');
        if (epNeighbour) {
          var enginePt = enginePtForVertex_(control, v);
          if (enginePt) {
            var gap = WCB.distance2D(enginePt.n, enginePt.e, epNeighbour.n, epNeighbour.e);
            if (gap <= SNAP_TOL) {
              pt = epNeighbour;
              note = 'ไม่มีแถว PT แยก; ใช้พิกัด EP แทน (engine-PT ตรงกับ EP ในระดับ ' +
                (gap * 1000).toFixed(2) + ' มม.)';
            }
          }
        }
      }

      var deltaDrawn = null;
      if (pc && pt) {
        var azInDrawn  = WCB.azimuthFromCoords(pc.n, pc.e, vert.n, vert.e);
        var azOutDrawn = WCB.azimuthFromCoords(vert.n, vert.e, pt.n, pt.e);
        deltaDrawn = FPMath.angleDiff(azOutDrawn, azInDrawn);
      } else if (!note) {
        var missing = pc ? 'PT' : 'PC';
        note = 'ไม่มีแถว ' + missing + ' ติดกับ PI; รัศมีใช้ Δ ออกแบบ';
      }

      var deltaForRadius = (deltaDrawn !== null) ? deltaDrawn : deltaDesign;
      var tooSmall = Math.abs(deltaForRadius) < 1e-9;
      if (tooSmall && !note) note = 'Δ เล็กเกินไป (PI เกือบตรง) — ไม่คำนวณรัศมี';

      var tIn  = pc ? WCB.distance2D(vert.n, vert.e, pc.n, pc.e) : null;
      var tOut = pt ? WCB.distance2D(vert.n, vert.e, pt.n, pt.e) : null;

      function radiusFromTangent(t) {
        if (t === null || tooSmall) return null;
        var half = Math.abs(deltaForRadius) / 2;
        var sign = deltaForRadius >= 0 ? 1 : -1;
        return sign * (t / Math.tan(half));
      }

      var rIn  = radiusFromTangent(tIn);
      var rOut = radiusFromTangent(tOut);

      // ΔRadius = |R_calc| − |R_design| (ไม่ใช่ค่ามีเครื่องหมายตรงๆ — แผนที่
      // อนุมัติ §3.2 เพราะ buildFromPI ไม่สนใจเครื่องหมาย R ในตารางเลย)
      var dRIn  = (rIn  === null) ? null : Math.abs(rIn)  - Math.abs(rDesign);
      var dROut = (rOut === null) ? null : Math.abs(rOut) - Math.abs(rDesign);

      // SignOK: ตรวจเครื่องหมาย R แยกต่างหาก ไม่ปนกับตัวเลข ΔRadius
      var signOk = true;
      if (deltaDrawn !== null) {
        var signDesign = rDesign >= 0 ? 1 : -1;
        var signDrawn  = deltaDrawn >= 0 ? 1 : -1;
        signOk = (signDesign === signDrawn);
      }

      out.push({
        name: rec.name,
        rDesign: rDesign,
        tIn: tIn, tOut: tOut,
        rIn: rIn, rOut: rOut,
        dRIn: dRIn, dROut: dROut,
        signOk: signOk,
        deflDesignDeg: FPMath.radToDeg(deltaDesign),
        deflDrawnDeg: (deltaDrawn === null) ? null : FPMath.radToDeg(deltaDrawn),
        dDeflDeg: (deltaDrawn === null) ? null : FPMath.radToDeg(deltaDrawn - deltaDesign),
        note: note
      });
    }
    return out;
  }

  function radiusToRows(checks) {
    var rows = [];
    for (var i = 0; i < checks.length; i++) {
      var c = checks[i];
      rows.push([
        c.name, c.rDesign, c.tIn, c.tOut, c.rIn, c.rOut,
        c.dRIn, c.dROut, c.signOk, c.note
      ]);
    }
    return rows;
  }

  // ตาราง 2c ไม่แสดงแถวที่ไม่มี Δ_drawn จริง (แผนที่อนุมัติ §3.1 — PI-1 ยังคง
  // ไม่มีแถวในตารางนี้เพราะไม่มีแถว PC ให้จับคู่)
  function deflectionToRows(checks) {
    var rows = [];
    for (var i = 0; i < checks.length; i++) {
      var c = checks[i];
      if (c.deflDrawnDeg === null) continue;
      rows.push([c.name, c.deflDesignDeg, c.deflDrawnDeg, c.dDeflDeg, c.dDeflDeg * 3600.0]);
    }
    return rows;
  }

  return {
    POINTS_HEADER: POINTS_HEADER,
    RADIUS_HEADER: RADIUS_HEADER,
    DEFLECTION_HEADER: DEFLECTION_HEADER,

    snapToAlignmentEnds_: snapToAlignmentEnds_,
    checkPoints: checkPoints,
    pointsToRows: pointsToRows,

    scanRawRows_: scanRawRows_,
    neighbourDrawingPoint_: neighbourDrawingPoint_,
    neighbourAnyPoint_: neighbourAnyPoint_,
    splitControlIntoPiGroups_: splitControlIntoPiGroups_,
    enginePtForVertex_: enginePtForVertex_,

    checkPiCurves: checkPiCurves,
    radiusToRows: radiusToRows,
    deflectionToRows: deflectionToRows
  };
})();

if (typeof module !== 'undefined' && module.exports) module.exports = GS_CrossCheck;
