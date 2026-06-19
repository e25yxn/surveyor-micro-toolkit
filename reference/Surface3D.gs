/**
 * ============================================================================
 *  Surface3D — จุด 3 มิติบนผิวถนน (รวมแนวราบ + ดิ่ง + การยกโค้ง)  [Phase 2.3]
 * ----------------------------------------------------------------------------
 *  รวมร่างทั้งระบบ:  (N,E) จากแนวราบ + ระดับ CL จาก Vertical + cross-fall (LT/RT)
 *  -> ระดับผิวถนน ณ จุดใดๆ (สถานี, offset)
 *
 *  cross-fall แยกเป็น 2 ตาราง: ฝั่งซ้าย (LT) และฝั่งขวา (RT)
 *    สูตร:  Lsurface = L_centerline + |offset| * crossfall(ฝั่งนั้น) / 100
 *    - offset: + = ขวาของทิศเดินทาง, - = ซ้าย (เหมือน FWD/SETOUT ฝั่งราบ)
 *      offset < 0 -> ใช้ตาราง LT ,  offset > 0 -> ใช้ตาราง RT ,  offset = 0 -> ระดับ CL
 *    - ใช้ |offset| (ระยะออกด้านนอก): cross-fall ค่าลบ = ขอบ "เทลง" (ต่ำกว่า CL)
 *    - รองรับทั้งหลังคาปกติ (LT,RT เป็นลบทั้งคู่) และยกโค้ง (เครื่องหมายต่างกัน)
 *      ด้วยกติกาเดียว — ไม่ต้องมีโหมด crown แยก
 *    - ใส่ด้านเดียวได้: ถ้าเว้น LT หรือ RT ว่างไว้ ระบบใช้ตารางที่มีกับทั้งสองด้าน
 *      (เหมาะเมื่อวางด้านเดียว หรือ cross-fall เท่ากันสองด้าน;
 *       ถ้ายกโค้งสองด้านต่างกันให้ใส่ทั้งคู่)
 *
 *  สร้างบน Alignment, Vertical, CrossFall (ใช้ public API)
 * ============================================================================
 */
if (typeof Alignment === 'undefined' && typeof require !== 'undefined') { var Alignment = require('./Alignment.gs'); }
if (typeof Vertical === 'undefined' && typeof require !== 'undefined')  { var Vertical = require('./Vertical.gs'); }
if (typeof CrossFall === 'undefined' && typeof require !== 'undefined') { var CrossFall = require('./CrossFall.gs'); }

var Surface3D = (function () {
  'use strict';

  // ระดับผิวที่ offset จาก CL  (ใช้ |offset| = ระยะออกด้านนอก)
  function surfaceLevel(clLevel, crossFallPct, offset) {
    return clLevel + Math.abs(offset) * crossFallPct / 100;
  }

  // จุด 3 มิติบนผิว ณ (sta, offset)
  //  elements = ตาราง element ราบ, vSegs = ดิ่ง, xLTsegs/xRTsegs = cross-fall ซ้าย/ขวา
  function point3D(elements, vSegs, xLTsegs, xRTsegs, sta, offset) {
    var off = offset || 0;
    var ne = Alignment.stationToCoord(elements, sta, off);     // N,E ที่ (sta, offset)
    var cl = Vertical.levelFromTable(vSegs, sta);              // ระดับ centerline
    var lv, xf = null;
    if (cl === null)      lv = null;
    else if (off === 0)   lv = cl;                             // อยู่บน CL
    else {
    var primary  = (off < 0) ? xLTsegs : xRTsegs;
    var fallback = (off < 0) ? xRTsegs : xLTsegs;        // ด้านที่ถามว่าง -> ใช้ด้านที่มี
    var xSegs = (primary && primary.length) ? primary
              : (fallback && fallback.length) ? fallback : null;
    xf = xSegs ? CrossFall.crossFallFromTable(xSegs, sta) : null;
    lv = (xf === null) ? null : surfaceLevel(cl, xf, off);
    }
    return { n: ne.n, e: ne.e, level: lv, clLevel: cl, crossFall: xf };
  }

  return { surfaceLevel: surfaceLevel, point3D: point3D };
})();

// ---- custom functions สำหรับเรียกในเซลล์ ----
function parseH_(table) {
  var els = [];
  for (var i = 0; i < table.length; i++) {
    var r = table[i];
    if (r[0] === '' || r[0] === null || r[0] === undefined || isNaN(Number(r[0]))) continue;
    els.push(Alignment.makeElement(String(r[6]).trim(), Number(r[0]), Number(r[1]),
             Number(r[2]), Number(r[3]), Number(r[4]), Number(r[5]), undefined, r[7]));
  }
  return els;
}

/** ระดับผิวถนน ณ (sta, offset).  =SLEVEL(V_ROR4, X_ROR4_LT, X_ROR4_RT, sta, offset)
 *  (ใช้ร่วมกับ FWD_N/FWD_E ที่มีอยู่เพื่อได้ N,E) */
function SLEVEL(vTable, xLT, xRT, sta, offset) {
  if (sta === '' || sta === null || sta === undefined) return '';
  var off = Number(offset) || 0;
  var cl = Vertical.levelFromTable(parseVertical_(vTable), Number(sta));
  if (cl === null) return '#STA_OUT';
  if (off === 0) return cl;
  var lt = parseCrossFall_(xLT), rt = parseCrossFall_(xRT);
  var primary = (off < 0) ? lt : rt, fallback = (off < 0) ? rt : lt;
  var xSegs = primary.length ? primary : (fallback.length ? fallback : null);
  if (!xSegs) return '#NO_XFALL';                          // ไม่มี cross-fall ทั้งสองด้าน
  var xf = CrossFall.crossFallFromTable(xSegs, Number(sta));
  if (xf === null) return '#STA_OUT';
  return Surface3D.surfaceLevel(cl, xf, off);
}

/** จุด 3 มิติเต็ม: คืน [N, E, Level] (กระจาย 3 ช่อง)
 *  =P3D(ORR4_h, V_ROR4, X_ROR4_LT, X_ROR4_RT, sta, offset) */
function P3D(hTable, vTable, xLT, xRT, sta, offset) {
  if (sta === '' || sta === null || sta === undefined) return '';
  var off = Number(offset) || 0;
  var p = Surface3D.point3D(parseH_(hTable), parseVertical_(vTable),
                            parseCrossFall_(xLT), parseCrossFall_(xRT), Number(sta), off);
  return [[p.n, p.e, p.level === null ? '#STA_OUT' : p.level]];
}

if (typeof module !== 'undefined' && module.exports) module.exports = Surface3D;
