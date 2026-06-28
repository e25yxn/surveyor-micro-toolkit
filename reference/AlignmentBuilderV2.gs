/**
 * EXT-001: no-curve PI support — mirrors Python alignment_builder.py (commit cdf896d)
 *
 * ============================================================================
 *  AlignmentBuilderV2 — สร้างตาราง element จากเส้นโครง PI (แนว B)   [v2.0]
 * ----------------------------------------------------------------------------
 *  รับ: PI polyline = [BP, {PI,...}, ..., EP]
 *    - BP (จุดแรก) / EP (จุดท้าย) = จุดปลาย ไม่มีโค้ง  {sta,n,e}
 *    - จุดกลาง = PI แต่ละโค้ง รองรับ 4 แบบ:
 *        โค้งธรรมดา      : {sta,n,e, R}
 *        spiral สมมาตร   : {sta,n,e, R, Ls}            (Ls เข้า=ออก)
 *        spiral อสมมาตร  : {sta,n,e, R, LsIn, LsOut}   (เข้า≠ออก)
 *        compound        : {sta,n,e, compound:[{R,delta},{R}]}  (delta=องศา;
 *                          ตัวสุดท้ายไม่ต้องใส่ delta -> ใช้ส่วนที่เหลือ)
 *      (ใส่ trans / transIn / transOut เพื่อเลือกชนิด transition ของ spiral)
 *    - angle point (EXT-001) : {sta,n,e} ไม่มี R หรือ R=0 -> tangent + 'IP'
 *  คืน: { elements, control, issues }
 *
 *  หลักการวางโค้ง: สร้างโค้งในพิกัดท้องถิ่น (เริ่มที่ PI, az=azIn) ด้วย engine
 *    -> ได้เวกเตอร์ TS->ST = V  -> แก้ 2x2 หา d1,d2 ให้แตะ tangent สองเส้น
 *    -> วางจริง แล้วส่งทอด (Point Forwarding) หาจุด control ที่เหลือ
 *  วิธีนี้รองรับทุกโครงสร้างโค้ง + ทุกชนิด transition โดยอัตโนมัติ
 *
 *  สร้างบน FPMath, WCB, Alignment (ใช้ public API)
 * ============================================================================
 */
if (typeof FPMath === 'undefined' && typeof require !== 'undefined')    { var FPMath = require('./FPMath.gs'); }
if (typeof WCB === 'undefined' && typeof require !== 'undefined')       { var WCB = require('./WCB.gs'); }
if (typeof Alignment === 'undefined' && typeof require !== 'undefined') { var Alignment = require('./Alignment.gs'); }

var AlignmentBuilderV2 = (function () {
  'use strict';

  // แตกโครงสร้างโค้งที่ PI ออกเป็นรายการ sub-element (kind, R, len, trans)
  // absD = มุมเลี้ยวรวม (รัศมีบวก), คืน {subs, issue}
  function curveSubs_(vert, absD) {
    var subs = [], issue = null;

    if (vert.compound && vert.compound.length) {
      var used = 0, arcs = vert.compound;
      for (var i = 0; i < arcs.length; i++) {
        var Rc = Math.abs(arcs[i].R), dlt;
        if (i < arcs.length - 1) { dlt = FPMath.degToRad(arcs[i].delta); used += dlt; }
        else { dlt = absD - used; }
        if (dlt < 0) issue = 'compound: ผลรวม delta เกินมุมเลี้ยว';
        subs.push({ kind: 'C', R: Rc, len: Rc * dlt });
      }
      return { subs: subs, issue: issue };
    }

    // EXTENSION: beyond oracle — treat missing R or R=0 as angle point
    if (!vert.compound && (!vert.R || parseFloat(vert.R) === 0)) {
      return { subs: [], issue: null };
    }

    var R = Math.abs(vert.R);
    var LsIn  = (vert.LsIn  != null) ? vert.LsIn  : (vert.Ls || 0);
    var LsOut = (vert.LsOut != null) ? vert.LsOut : (vert.Ls || 0);

    if (LsIn > 0 || LsOut > 0) {
      var thIn  = LsIn  > 0 ? LsIn  / (2 * R) : 0;
      var thOut = LsOut > 0 ? LsOut / (2 * R) : 0;
      var dc = absD - thIn - thOut;
      if (dc < 0) issue = 'spiral ยาวเกินมุมเลี้ยว (Δ < θsIn+θsOut)';
      if (LsIn  > 0) subs.push({ kind: 'SPIN',  R: R, len: LsIn,  trans: vert.transIn  || vert.trans });
      subs.push({ kind: 'C', R: R, len: R * dc });
      if (LsOut > 0) subs.push({ kind: 'SPOUT', R: R, len: LsOut, trans: vert.transOut || vert.trans });
      return { subs: subs, issue: issue };
    }

    subs.push({ kind: 'C', R: R, len: R * absD });           // โค้งธรรมดา
    return { subs: subs, issue: issue };
  }

  // ตั้งชื่อจุด control ตามโครงสร้าง subs
  function names_(subs) {
    // EXTENSION: beyond oracle — guard empty subs (angle point)
    if (!subs || subs.length === 0) {
      return { start: 'IP', end: 'IP', jct: [] };
    }
    var start = subs[0].kind === 'SPIN' ? 'TS' : 'PC';
    var end   = subs[subs.length - 1].kind === 'SPOUT' ? 'ST' : 'PT';
    var jct = [];
    for (var i = 0; i < subs.length - 1; i++) {
      var a = subs[i].kind, b = subs[i + 1].kind;
      if (a === 'SPIN' && b === 'C') jct.push('SC');
      else if (a === 'C' && b === 'SPOUT') jct.push('CS');
      else if (a === 'C' && b === 'C') jct.push('PCC');
      else jct.push('JCT');
    }
    return { start: start, end: end, jct: jct };
  }

  // สร้างโค้งในพิกัดท้องถิ่น (เริ่ม origin, az=azIn) -> เวกเตอร์ปลาย V (TS->ST)
  function endDisp_(subs, azIn, sgn) {
    var cur = { n: 0, e: 0, az: azIn }, sta = 0;
    for (var i = 0; i < subs.length; i++) {
      var s = subs[i];
      var el = Alignment.makeElement(s.kind, sta, sta + s.len, cur.n, cur.e,
                                     FPMath.radToDeg(cur.az), sgn * s.R, undefined, s.trans);
      cur = Alignment.exitState(el);
      sta += s.len;
    }
    return { n: cur.n, e: cur.e };
  }

  function buildFromPI(vertices) {
    var els = [], control = [], issues = [];
    var N = vertices.length;
    var prev = { n: vertices[0].n, e: vertices[0].e, sta: vertices[0].sta };
    control.push({ name: 'BP', sta: prev.sta, n: prev.n, e: prev.e });

    for (var v = 1; v < N - 1; v++) {
      var Vn = vertices[v].n, Ve = vertices[v].e;
      var azIn  = WCB.azimuthFromCoords(vertices[v - 1].n, vertices[v - 1].e, Vn, Ve);
      var azOut = WCB.azimuthFromCoords(Vn, Ve, vertices[v + 1].n, vertices[v + 1].e);
      var delta = FPMath.angleDiff(azOut, azIn);
      var sgn = delta >= 0 ? 1 : -1, absD = Math.abs(delta);

      var cs = curveSubs_(vertices[v], absD);
      if (cs.issue) issues.push('PI#' + v + ': ' + cs.issue);
      var subs = cs.subs;

      // EXTENSION: beyond oracle — angle point (no curve)
      // เกิดเมื่อ R หายหรือ R=0 (รวมถึง collinear PI ที่ delta=0)
      if (!subs || subs.length === 0) {
        var tanLen = WCB.distance2D(prev.n, prev.e, Vn, Ve);
        var staPi  = prev.sta + tanLen;
        els.push(Alignment.makeElement('T', prev.sta, staPi, prev.n, prev.e,
                                        FPMath.radToDeg(azIn), 0));
        control.push({ name: 'IP', sta: staPi, n: Vn, e: Ve });
        prev = { n: Vn, e: Ve, sta: staPi };
        continue;
      }

      // วางโค้ง: แก้ 2x2  d1*uIn + d2*uOut = V
      var V = endDisp_(subs, azIn, sgn);
      var det = Math.sin(delta);                    // = sin(azOut-azIn)
      var ciIn = Math.cos(azIn),  siIn = Math.sin(azIn);
      var coOut = Math.cos(azOut), soOut = Math.sin(azOut);
      var d1 = (V.n * soOut - V.e * coOut) / det;
      var curveStart = { n: Vn - d1 * ciIn, e: Ve - d1 * siIn };

      var nm = names_(subs);

      // tangent: prev -> curveStart
      var tanLen = WCB.distance2D(prev.n, prev.e, curveStart.n, curveStart.e);
      var staCS = prev.sta + tanLen;
      els.push(Alignment.makeElement('T', prev.sta, staCS, prev.n, prev.e, FPMath.radToDeg(azIn), 0));
      control.push({ name: nm.start, sta: staCS, n: curveStart.n, e: curveStart.e });

      // ส่งทอดสร้าง sub-element จริง พร้อมจุด control
      var cur = { n: curveStart.n, e: curveStart.e, az: azIn }, sta = staCS;
      for (var i = 0; i < subs.length; i++) {
        var s = subs[i];
        var el = Alignment.makeElement(s.kind, sta, sta + s.len, cur.n, cur.e,
                                       FPMath.radToDeg(cur.az), sgn * s.R, undefined, s.trans);
        els.push(el);
        cur = Alignment.exitState(el);
        sta += s.len;
        var ptName = (i < subs.length - 1) ? nm.jct[i] : nm.end;
        control.push({ name: ptName, sta: sta, n: cur.n, e: cur.e });
      }
      prev = { n: cur.n, e: cur.e, sta: sta };
    }

    var ep = vertices[N - 1];
    var azEnd = WCB.azimuthFromCoords(prev.n, prev.e, ep.n, ep.e);
    var endLen = WCB.distance2D(prev.n, prev.e, ep.n, ep.e);
    els.push(Alignment.makeElement('T', prev.sta, prev.sta + endLen, prev.n, prev.e, FPMath.radToDeg(azEnd), 0));
    control.push({ name: 'EP', sta: prev.sta + endLen, n: ep.n, e: ep.e });

    return { elements: els, control: control, issues: issues };
  }

  function crossCheck(control, drawing, tol) {
    if (tol === undefined) tol = 0.05;
    var report = [];
    // วนตาม "ค่าจากแบบ" ที่ผู้ใช้กรอก — กรอกกี่จุดก็เทียบเท่านั้น
    for (var j = 0; j < drawing.length; j++) {
      var d = drawing[j];
      var best = null, bestD = Infinity;
      for (var i = 0; i < control.length; i++) {
        var c = control[i];
        if (d.name && String(d.name).length && c.name !== d.name) continue; // ถ้าระบุชื่อ ให้ตรงชื่อ
        var dd = Math.abs(c.sta - d.sta);
        if (dd < bestD) { bestD = dd; best = c; }
      }
      if (!best) continue;
      var gap = Math.hypot(best.n - d.n, best.e - d.e);
      report.push({ name: d.name || best.name, staCalc: best.sta, staDraw: d.sta, gap_m: gap, ok: gap <= tol });
    }
    return report;
  }

  return { buildFromPI: buildFromPI, crossCheck: crossCheck };
})();

if (typeof module !== 'undefined' && module.exports) module.exports = AlignmentBuilderV2;
