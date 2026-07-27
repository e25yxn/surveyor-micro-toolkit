# BUNDLE_gsheet.md — Google Apps Script engine (concatenated, dependency order)

Generated from the working tree on 2026-07-27. Files pushed to `D:\MyClasp_SMT_DEMO\`
as `FPMath.js`, `WCB.js`, `GS_Alignment.js`, `GS_AlignmentBuilder.js`,
`GS_TableSplitter.js`, `GS_PiTableParser.js`, `GS_ElementTable.js`, `GS_CrossCheck.js`.
Order below is a valid dependency order (every file's `require()` targets appear
earlier in this document) — verified by grepping `require\(` across
`reference/` + `reference/gsheet/` before assembly (see DEPENDENCY_MAP.md).

---

## FILE: reference/FPMath.gs
```gs
/**
 * ============================================================================
 *  FPMath — FP-safe math utilities  (Geometry Core / ชั้นล่างสุด)
 * ----------------------------------------------------------------------------
 *  ปรัชญา (ตรงกับ core concept: SAFE + SMALL + STABLE):
 *    1) ภายในคำนวณด้วย full IEEE 754 (float64) เสมอ "ห้ามปัดเศษกลางทาง"
 *    2) ปัดเศษเฉพาะตอน "ส่งออก" (export/display) เท่านั้น
 *    3) ทุกฟังก์ชันเป็น pure function: ใส่ค่าเดิม -> ได้ผลเดิม ไม่มี side effect
 *       => ทดสอบครั้งเดียวจบ, นำกลับมาใช้ซ้ำได้ทุกที่
 *
 *  หน่วยมาตรฐานภายใน engine:
 *    - มุม (angle)  : radian  (เพราะ Math.sin/cos/atan2 ของ JS ใช้ radian)
 *    - เก็บ/แสดงมุม : packed DMS เช่น 120.012256  = 120°01'22.56"
 *
 *  ใช้งานได้ทั้งใน Google Apps Script และ Node.js (ดู export ท้ายไฟล์)
 * ============================================================================
 */
var FPMath = (function () {
  'use strict';

  // ---- ค่าคงที่ ----------------------------------------------------------
  var EPS     = 1e-9;            // tolerance เริ่มต้นสำหรับเทียบ float
                                 // (เหลือ ~6 หลักจาก 15 หลัก เผื่อ error สะสม)
  var TWO_PI  = 2 * Math.PI;
  var DEG2RAD = Math.PI / 180;
  var RAD2DEG = 180 / Math.PI;

  // =========================================================================
  //  ROUNDING — ปัดเศษ (ใช้ตอนส่งออกเท่านั้น)
  // =========================================================================

  /**
   * ปัดเศษแบบ "round half away from zero" (ครึ่งหนึ่งปัดออกจากศูนย์)
   *  - เลือกวิธีนี้เพราะ "สมมาตร" และคาดเดาได้ ตรงกับสัญชาตญาณนักสำรวจ
   *    (2.5 -> 3,  -2.5 -> -3)  ต่างจาก Math.round ปกติที่ -2.5 -> -2
   *
   *  ใช้เทคนิค exponential-string แทนการคูณ 10^n ตรงๆ เพื่อเลี่ยงบั๊กคลาสสิก:
   *    roundTo(1.005, 2) ถ้าใช้ Math.round(1.005*100)/100 จะได้ 1.00 (ผิด!)
   *    เพราะ 1.005 ถูกเก็บเป็น 1.00499999... การเลื่อนผ่าน string ช่วยกันพลาดนี้
   */
  function roundTo(value, decimals) {
    if (decimals === undefined) decimals = 3;
    if (!isFinite(value)) return value;
    var sign = value < 0 ? -1 : 1;
    var shifted = Number(Math.abs(value) + 'e' + decimals);
    return sign * Number(Math.round(shifted) + 'e-' + decimals);
  }

  /**
   * ตัดทศนิยมทิ้ง (ไม่ปัด) — ใช้กับการแสดง STATION เช่น 1+000.999 ไม่ให้ปัดขึ้นเป็น 1+001.000
   */
  function truncTo(value, decimals) {
    if (decimals === undefined) decimals = 3;
    if (!isFinite(value)) return value;
    var sign = value < 0 ? -1 : 1;
    var shifted = Number(Math.abs(value) + 'e' + decimals);
    return sign * Number(Math.trunc(shifted) + 'e-' + decimals);
  }

  // =========================================================================
  //  COMPARISON — เปรียบเทียบ float อย่างปลอดภัย
  // =========================================================================

  /**
   * เทียบว่า a ~ b หรือไม่ โดยผสม absolute + relative tolerance
   *  - absolute : จำเป็นเมื่อค่าใกล้ 0 (relative อย่างเดียวจะหารด้วยเกือบศูนย์)
   *  - relative : จำเป็นเมื่อค่าใหญ่ เช่น พิกัด 1,537,540 (absolute 1e-9 จะเข้มเกินไป)
   *  => จึงใช้ทั้งคู่ เลือกอันที่หลวมกว่า
   */
  function almostEqual(a, b, eps) {
    if (eps === undefined) eps = EPS;
    var diff = Math.abs(a - b);
    if (diff <= eps) return true;                         // เคสใกล้ 0
    return diff <= eps * Math.max(Math.abs(a), Math.abs(b)); // เคสค่าใหญ่
  }

  /**
   * เช็คว่า value อยู่ในช่วง [min, max] ไหม (เผื่อ tolerance ที่ขอบ)
   *  - ใช้ตอนหาว่า station อยู่ใน element ไหน: ขอบ element ต้องไม่ "พลาดเฉียด"
   */
  function inRange(value, min, max, eps) {
    if (eps === undefined) eps = EPS;
    return value >= (min - eps) && value <= (max + eps);
  }

  // =========================================================================
  //  MODULAR / ANGLE — จัดการมุมและ modulo ให้ถูกต้องเรื่องเครื่องหมาย
  // =========================================================================

  /**
   * modulo ที่ผลลัพธ์เป็นบวกเสมอ (ต่างจาก % ของ JS ที่ติดเครื่องหมายตัวตั้ง)
   *  mod(-1, 4) = 3   แต่   -1 % 4 = -1
   */
  function mod(a, n) {
    return ((a % n) + n) % n;
  }

  /**
   * บีบมุม (radian) ให้อยู่ในช่วง [0, 2π)
   *  - azimuth 359.9° + 0.2° ต้องได้ 0.1°  ไม่ใช่ 360.1°
   */
  function normalizeAngle(rad) {
    return mod(rad, TWO_PI);
  }

  /**
   * ผลต่างมุมที่ "สั้นที่สุด" (a - b) อยู่ในช่วง (-π, π]
   *  - ใช้ตรวจ tangent continuity: ผลต่าง azimuth ข้าม 0°/360° ต้องไม่เพี้ยน
   */
  function angleDiff(a, b) {
    return mod(a - b + Math.PI, TWO_PI) - Math.PI;
  }

  // =========================================================================
  //  SAFE ARITHMETIC — ลดการสะสมความคลาดเคลื่อน (Error Propagation)
  // =========================================================================

  /**
   * Kahan summation — บวกเลขชุดยาวโดยดึง error ที่ปัดทิ้งกลับมาชดเชย
   *  - สำคัญเมื่อรวมความยาว element หลายสิบช่วงเป็น station รวม
   *    การบวกธรรมดาจะสะสม round-off ทีละนิดจนเพี้ยนระดับ มม. ในงานยาวๆ
   */
  function kahanSum(values) {
    var sum = 0, comp = 0;       // comp = error ที่ค้างไว้ชดเชยรอบถัดไป
    for (var i = 0; i < values.length; i++) {
      var y = values[i] - comp;
      var t = sum + y;
      comp = (t - sum) - y;      // ส่วนที่ปัดหายไป ดึงกลับมาเก็บ
      sum = t;
    }
    return sum;
  }

  // =========================================================================
  //  CONVERSION — แปลงหน่วยมุม
  // =========================================================================

  function degToRad(deg) { return deg * DEG2RAD; }
  function radToDeg(rad) { return rad * RAD2DEG; }

  /**
   * แปลง packed DMS -> radian   เช่น 120.012256 -> rad ของ 120°01'22.56"
   *  - รูปแบบ packed: D.MMSSsss  (MM=ลิปดา 2 หลัก, SS.sss=ฟิลิปดา)
   *  - ปัญหา FP: 120.012256 อาจถูกเก็บเป็น 120.01225599999...
   *    ถ้าแยกหลักตรงๆ จะได้ฟิลิปดาเพี้ยน -> ต้อง roundTo คุมตอนแยกหลัก
   */
  function packedDMSToRad(packed, secDecimals) {
    if (secDecimals === undefined) secDecimals = 4;
    var sign = packed < 0 ? -1 : 1;
    var a = Math.abs(packed);
    var d = Math.trunc(a);
    // เลื่อนทศนิยม 2 ตำแหน่ง: .MMSSsss -> MM.SSsss  แล้วคุม noise
    var r1 = roundTo((a - d) * 100, secDecimals + 2);
    var m = Math.trunc(r1);
    var s = roundTo((r1 - m) * 100, secDecimals);   // .SSsss -> SS.sss
    var decimalDeg = d + m / 60 + s / 3600;
    return sign * decimalDeg * DEG2RAD;
  }

  /**
   * แปลง radian -> packed DMS   เช่น rad ของ 120°01'22.56" -> 120.012256
   *  - ปัดวินาทีก่อน แล้ว "ทด" ถ้าถึง 60 (วินาที->ลิปดา, ลิปดา->องศา)
   */
  function radToPackedDMS(rad, secDecimals) {
    if (secDecimals === undefined) secDecimals = 2;
    var deg = rad * RAD2DEG;
    var sign = deg < 0 ? -1 : 1;
    deg = Math.abs(deg);
    var d = Math.trunc(deg);
    var mFull = (deg - d) * 60;
    var m = Math.trunc(mFull);
    var s = roundTo((mFull - m) * 60, secDecimals);
    if (s >= 60) { s -= 60; m += 1; }                // ทดวินาที
    if (m >= 60) { m -= 60; d += 1; }                // ทดลิปดา
    var packed = d + m / 100 + s / 10000;
    return sign * roundTo(packed, secDecimals + 4);
  }

  /**
   * แปลง radian -> ข้อความ DMS สวยงาม เช่น "120°01'22.56\""
   */
  function radToDMSString(rad, secDecimals) {
    if (secDecimals === undefined) secDecimals = 2;
    var deg = rad * RAD2DEG;
    var sign = deg < 0 ? '-' : '';
    deg = Math.abs(deg);
    var d = Math.trunc(deg);
    var mFull = (deg - d) * 60;
    var m = Math.trunc(mFull);
    var s = roundTo((mFull - m) * 60, secDecimals);
    if (s >= 60) { s -= 60; m += 1; }
    if (m >= 60) { m -= 60; d += 1; }
    var ss = s.toFixed(secDecimals);
    if (s < 10) ss = '0' + ss;                       // เติม 0 หน้าวินาที
    var mm = (m < 10 ? '0' : '') + m;
    return sign + d + '\u00B0' + mm + '\u2032' + ss + '\u2033';
  }

  /**
   * แปลงองค์ประกอบ D, M, S -> radian
   */
  function dmsToRad(d, m, s) {
    if (m === undefined) m = 0;
    if (s === undefined) s = 0;
    var sign = d < 0 ? -1 : 1;
    var decimalDeg = Math.abs(d) + m / 60 + s / 3600;
    return sign * decimalDeg * DEG2RAD;
  }

  // ---- public API --------------------------------------------------------
  return {
    EPS: EPS, TWO_PI: TWO_PI, DEG2RAD: DEG2RAD, RAD2DEG: RAD2DEG,
    roundTo: roundTo,
    truncTo: truncTo,
    almostEqual: almostEqual,
    inRange: inRange,
    mod: mod,
    normalizeAngle: normalizeAngle,
    angleDiff: angleDiff,
    kahanSum: kahanSum,
    degToRad: degToRad,
    radToDeg: radToDeg,
    packedDMSToRad: packedDMSToRad,
    radToPackedDMS: radToPackedDMS,
    radToDMSString: radToDMSString,
    dmsToRad: dmsToRad
  };
})();

// ให้ require() ใน Node.js ได้ (Apps Script จะข้ามบรรทัดนี้ไปเอง)
if (typeof module !== 'undefined' && module.exports) module.exports = FPMath;
```

---

## FILE: reference/WCB.gs
```gs
/**
 * ============================================================================
 *  WCB — Azimuth / Coordinate Geometry  (Geometry Core)
 * ----------------------------------------------------------------------------
 *  Azimuth (WCB = Whole Circle Bearing): เริ่ม 0 ที่ทิศเหนือ วนขวาตามเข็มนาฬิกา
 *    ทิศเหนือ=0°  ทิศตะวันออก=90°  ทิศใต้=180°  ทิศตะวันตก=270°
 *
 *  สะพานจาก Casio fx-5800p:
 *    inverseCompute  ≈  Pol(ΔN, ΔE)   (สองจุด -> ได้ทั้งมุมและระยะ)
 *    forwardCompute  ≈  Rec(d, az)    (มุม+ระยะ -> ได้พิกัด)
 *
 *  หน่วยมุมภายใน = radian (เพราะ Math.sin/cos/atan2 ใช้ radian)
 *  แปลงเป็น/จาก DMS ด้วย FPMath เมื่อรับเข้า-ส่งออก
 * ============================================================================
 */

// รองรับทั้ง Apps Script (FPMath เป็น global อยู่แล้ว) และ Node (ต้อง require)
if (typeof FPMath === 'undefined' && typeof require !== 'undefined') {
  var FPMath = require('./FPMath.gs');
}

var WCB = (function () {
  'use strict';

  /**
   * azimuthFromCoords — หา azimuth (radian) จากจุด1 ไป จุด2
   *  วัดจากเหนือ วนขวา => ใช้ atan2(ΔE, ΔN)  (ไม่ใช่ atan2(ΔN, ΔE))
   *  คืนค่าในช่วง [0, 2π)
   *  (เทียบ Casio: นี่คือค่า θ ที่ได้จาก Pol)
   */
  function azimuthFromCoords(n1, e1, n2, e2) {
    var az = Math.atan2(e2 - e1, n2 - n1);
    return FPMath.normalizeAngle(az);
  }

  /**
   * distance2D — ระยะราบระหว่างสองจุด
   *  ใช้ Math.hypot กัน overflow/underflow ได้ดีกว่า sqrt(dn*dn + de*de)
   *  (เทียบ Casio: ค่า r ที่ได้จาก Pol)
   */
  function distance2D(n1, e1, n2, e2) {
    return Math.hypot(n2 - n1, e2 - e1);
  }

  /**
   * distance3D — ระยะตรง (slope distance) รวมความต่างระดับ Z
   */
  function distance3D(n1, e1, z1, n2, e2, z2) {
    return Math.hypot(n2 - n1, e2 - e1, z2 - z1);
  }

  /**
   * forwardCompute — จากจุดตั้ง + azimuth(radian) + ระยะ -> จุดใหม่ { n, e }
   *  ΔN = d·cos(az)   ΔE = d·sin(az)
   *  (เทียบ Casio: นี่คือ Rec(distance, azimuth))
   */
  function forwardCompute(n1, e1, azimuth, distance) {
    return {
      n: n1 + distance * Math.cos(azimuth),
      e: e1 + distance * Math.sin(azimuth)
    };
  }

  /**
   * inverseCompute — จากสองจุด -> { azimuth(radian), distance }
   *  (เทียบ Casio: นี่คือ Pol เต็มรูปแบบ ได้ทั้ง r และ θ พร้อมกัน)
   */
  function inverseCompute(n1, e1, n2, e2) {
    return {
      azimuth: azimuthFromCoords(n1, e1, n2, e2),
      distance: distance2D(n1, e1, n2, e2)
    };
  }

  /**
   * pointAtOffset — จุดที่เดินตาม azimuth เป็นระยะ along
   *                 แล้วเยื้องตั้งฉาก offset (+ = ขวามือ, - = ซ้ายมือ)
   *  ใช้บ่อยในงานวางตำแหน่ง: center line ทาบ offset ไปขอบถนน/ขอบสะพาน
   *  ขวามือของทิศเดิน = azimuth + 90°
   */
  function pointAtOffset(n1, e1, azimuth, along, offset) {
    var cl = forwardCompute(n1, e1, azimuth, along);   // จุดบน center line
    if (!offset) return cl;
    var offAz = FPMath.normalizeAngle(azimuth + Math.PI / 2);
    return forwardCompute(cl.n, cl.e, offAz, offset);
  }

  return {
    azimuthFromCoords: azimuthFromCoords,
    distance2D: distance2D,
    distance3D: distance3D,
    forwardCompute: forwardCompute,
    inverseCompute: inverseCompute,
    pointAtOffset: pointAtOffset
  };
})();

if (typeof module !== 'undefined' && module.exports) module.exports = WCB;
```

---

## FILE: reference/gsheet/GS_Alignment.gs
```gs
/**
 * ============================================================================
 *  GS_Alignment — Alignment Engine (Horizontal), Google Apps Script port
 * ----------------------------------------------------------------------------
 *  มิเรอร์จาก reference/Alignment.gs (oracle, frozen, ห้ามแก้) เพิ่ม COSINE
 *  (Civil 3D Sine Half-Wave) closed-form + arc-length inversion ให้ตรงกับ
 *  src/smt/alignment.py หลัง commit ba5de3c — เทียบเท่า Phase 4 ของ VBA
 *  (reference/vba/SMT_Alignment.bas, commit e285fd5) ที่พอร์ตส่วนเดียวกันไปแล้ว
 *
 *  ต่างจาก VBA Phase 4 ตรงที่ COSINE arc-length table ใช้ native Map แทนการ
 *  bisect ตรงทุกครั้ง — GAS V8 runtime มี Map จริง (ยืนยันแล้วใน
 *  session_logs/investigate_gsheet_port_scope.md §4) จึง cache ได้เหมือน
 *  Python's lru_cache แทนที่ VBA ซึ่งไม่มีเทียบเท่าจึงเลือกไม่ cache
 *
 *  ขอบเขต: เฉพาะ COSINE closed-form + arc-length inversion เท่านั้น (เหมือน VBA
 *  Phase 4 เป๊ะ) ไม่รวม EXT-002 (fit_radius) หรือ LandXML export
 *  ดู session_logs/investigate_gsheet_port_scope.md, session_logs/plan_20260713_0257.md
 *
 *  โมเดล: แนวเส้นทาง = ลิสต์ของ element ที่ต่อเรียงกัน (List of Elements)
 *  กฎเหล็ก (Point Forwarding): Exit State ของ element(n) = Entry State ของ element(n+1)
 *  แต่ละ element อธิบายด้วย "ความโค้ง" curvature (k = 1/R):
 *    Tangent      : kIn=0,    kOut=0
 *    Circular     : kIn=1/R,  kOut=1/R    (เท่ากัน)
 *    Spiral เข้า  : kIn=0,    kOut=1/R
 *    Spiral ออก   : kIn=1/R,  kOut=0
 *  เครื่องหมาย: k บวก = เลี้ยวขวา (azimuth เพิ่ม), k ลบ = เลี้ยวซ้าย
 *
 *  สร้างบน FPMath และ WCB (ดู reference/FPMath.gs, reference/WCB.gs — ต้อง import
 *  เข้า Apps Script project เดียวกันด้วย ไม่ได้ copy ซ้ำในไฟล์นี้)
 * ============================================================================
 */
if (typeof FPMath === 'undefined' && typeof require !== 'undefined') { var FPMath = require('../FPMath.gs'); }
if (typeof WCB === 'undefined' && typeof require !== 'undefined')    { var WCB = require('../WCB.gs'); }

var GS_Alignment = (function () {
  'use strict';

  var SPIRAL_STEPS = 48;   // จำนวนช่วง Simpson สำหรับ integrate spiral (คู่; 48 ละเอียดระดับไมครอน)
  var SINE_HALFWAVE_C = 0.0226689447;   // Civil 3D closed-form tangent-length correction constant

  // ---- รูปร่างการเปลี่ยน curvature (transition shape) ----
  //  curvature ที่สัดส่วน τ = s/L :  k = kIn + (kOut-kIn)*f(τ)   โดย f(0)=0, f(1)=1
  //  ทุกชนิดมี ∫₀¹ f = 1/2 เท่ากัน  => มุมเลี้ยวรวมเท่ากัน (ปลายทางมุมเดียวกัน)
  //  ต่างกันแค่ "เส้นทาง": Bloss/cosine/sine ลาดเข้า-ออกนุ่มกว่า (jerk ที่ปลาย = 0)
  //  shapeIntegral_ = F(τ) = ∫₀^τ f(u) du  (ใช้คำนวณมุมเลี้ยวแบบ closed-form)
  function shapeIntegral_(trans, tau) {
    var PI = Math.PI;
    switch (trans) {
      case 'BLOSS':  return tau*tau*tau - tau*tau*tau*tau/2;            // f=3τ²-2τ³
      // หมายเหตุ สูตร COSINE ในไฟล์นี้เป็นจุดอ้างอิงประวัติศาสตร์ที่แช่แข็งไว้ตามที่ตกลงกันไว้
      // ไม่ใช่ค่าที่ตรงกับ Civil 3D จริง (Civil 3D ใช้สูตรปิด Sine Half-Wavelength ที่ผูกกับ
      // ระยะโปรเจกชันบนเส้นสัมผัส ไม่ใช่ arc length integral แบบนี้) ดูรายละเอียดการแก้ที่
      // docs/extensions.md หัวข้อ EXT-003 และ session_logs/investigate_sinehalfwave_formula.md
      // ห้ามใช้ไฟล์นี้เป็นจุดอ้างอิงสำหรับ COSINE ให้ใช้ src/smt/alignment.py แทน
      case 'COSINE': return tau/2 - Math.sin(PI*tau)/(2*PI);           // f=(1-cos πτ)/2
      case 'SINE':   return tau*tau/2 - (1 - Math.cos(2*PI*tau))/(4*PI*PI); // f=τ-sin(2πτ)/2π
      default:       return tau*tau/2;                                  // CLOTHOID: f=τ (เชิงเส้น)
    }
  }

  // มุมเลี้ยวสะสม θ(s) = kIn*s + (kOut-kIn)*L*F(s/L)
  function thetaAt_(el, s) {
    var L = el.staEnd - el.staStart;
    var tau = (L === 0) ? 0 : s / L;
    return el.kIn * s + (el.kOut - el.kIn) * L * shapeIntegral_(el.trans, tau);
  }

  // แปลงรัศมี <-> curvature.  R=0/ว่าง/อนันต์ = tangent => k=0
  function curvatureFromRadius(r) {
    if (!r || !isFinite(r)) return 0;
    return 1 / r;
  }
  function radiusFromCurvature(k) {
    return (k === 0) ? Infinity : 1 / k;
  }

  // ============================================================
  // COSINE (Civil 3D Sine Half-Wave) closed-form helpers — NEW
  // Mirrors src/smt/alignment.py (_cosine_dydx, _cosine_arc_length,
  // _cosine_arc_length_table, _cosine_solve_a,
  // calculate_sine_halfwave_tangent_length, _sine_halfwave_point) after
  // commit ba5de3c. Uses a module-level Map as the arc-length-table cache
  // (Python's lru_cache equivalent) — unlike reference/vba/SMT_Alignment.bas
  // Phase 4, which has no Map/Dictionary equivalent and bisects on [0,1]
  // directly every call instead.
  // ============================================================

  var cosineArcLengthTableCache_ = new Map();

  // dy/dx at normalised parameter a — same expression as the atan() argument
  // in sineHalfwavePoint_'s theta (tan(theta) = dy/dx).
  function cosineDydx_(a, bigX, r) {
    return bigX / r * (a / 2 - Math.sin(Math.PI * a) / (2 * Math.PI));
  }

  // s(a) = integral[0..a] X*sqrt(1+(dy/dx)^2) da'  via Simpson quadrature.
  // Same 48-interval Simpson pattern already used in pointOnElement's spiral
  // branch below. Sign of r does not matter (dy/dx is squared inside the
  // root) -- callers building the cached table pass abs(r).
  function cosineArcLength_(a, bigX, r, nSeg) {
    if (nSeg === undefined) nSeg = SPIRAL_STEPS;
    var h = a / nSeg;
    var total = 0;
    for (var i = 0; i <= nSeg; i++) {
      var ai = i * h;
      var integrand = bigX * Math.hypot(1, cosineDydx_(ai, bigX, r));
      var w = (i === 0 || i === nSeg) ? 1 : (i % 2 === 1 ? 4 : 2);
      total += w * integrand;
    }
    return total * h / 3;
  }

  // Cached s(a_i) at a_i = i/SPIRAL_STEPS, i=0..SPIRAL_STEPS, for one
  // (length, |R|) pair. Shared by SPIN and SPOUT of equal length and |R|
  // (mirror symmetry), so a compound alignment using both only builds the
  // table once. Cache key is the plain string 'length|rAbs' (no rounding —
  // matches Python's exact-float tuple key (length, r_abs)).
  function cosineArcLengthTableGet_(length, rAbs) {
    var key = length + '|' + rAbs;
    var cached = cosineArcLengthTableCache_.get(key);
    if (cached) return cached;
    var bigX = calcSineHalfwaveTangentLength(length, rAbs);
    var n = SPIRAL_STEPS;
    var table = [];
    for (var i = 0; i <= n; i++) table.push(cosineArcLength_(i / n, bigX, rAbs));
    cosineArcLengthTableCache_.set(key, table);
    return table;
  }

  // Debug/testing only — number of distinct (length,|R|) entries cached so
  // far. Used by reference/gsheet/smoke_test.js to verify SPIN/SPOUT of
  // equal length/|R| share one cache entry.
  function cosineCacheSize_() {
    return cosineArcLengthTableCache_.size;
  }

  // Solve s(a) = d for normalised parameter a: cached-table bracket + 50
  // iteration bisection (same style as projectToElement's spiral bisection
  // below). d must satisfy 0 <= d < length (the d==length case is
  // short-circuited by the caller, sineHalfwavePoint_).
  function cosineSolveA_(d, bigX, r, length) {
    var rAbs = Math.abs(r);
    var table = cosineArcLengthTableGet_(length, rAbs);
    var n = SPIRAL_STEPS;
    var i = 0;
    while (i < n && table[i + 1] < d) i++;
    // When d lies in (s(1), length) -- s(1) != length exactly, a genuine
    // small imperfection in Autodesk's own closed-form X, not a quadrature
    // artifact (see session_logs/investigate_cosine_arclength_inversion.md
    // §3) -- the while loop runs to i=n, giving lo=hi=1: the bracket is
    // degenerate but bisection below is still safe (mid=1 every iteration).
    // This deliberately clamps to a=1.0 in that gap instead of erroring.
    var lo = i / n, hi = Math.min(i + 1, n) / n;
    for (var iter = 0; iter < 50; iter++) {
      var mid = (lo + hi) / 2;
      if (cosineArcLength_(mid, bigX, rAbs) < d) lo = mid; else hi = mid;
    }
    return (lo + hi) / 2;
  }

  // Closed-form tangent-projected length X for the COSINE transition shape,
  // at the element's own true end (arc length = length). Public (no
  // trailing underscore) so it is also usable directly from the UDF wrapper
  // GS_COSINE_TANGENT_LENGTH below.
  function calcSineHalfwaveTangentLength(length, r) {
    return length - SINE_HALFWAVE_C * length * length * length / (r * r);
  }

  // COSINE transition shape (Civil 3D Sine Half-Wave), canonical (SPIN)
  // form. d = true arc distance from the zero-curvature end. Returns
  // {x, y, theta}: true tangent-projected coordinate x=a*X, local offset y
  // (+ left of entry tangent), tangent angle theta (rad), all measured from
  // the zero-curvature end.
  function sineHalfwavePoint_(d, bigX, r, length) {
    var a;
    if (Math.abs(d - length) < 1e-9) {
      a = 1.0;
    } else {
      a = cosineSolveA_(d, bigX, r, length);
    }
    var y = bigX * bigX / r * (a * a / 4 - (1 - Math.cos(Math.PI * a)) / (2 * Math.PI * Math.PI));
    var theta = Math.atan(cosineDydx_(a, bigX, r));
    var x = a * bigX;
    return { x: x, y: y, theta: theta };
  }

  /**
   * สร้าง element 1 ตัว  (เก็บ azimuth เป็น radian, curvature ภายใน)
   *  azDeg = azimuth ขาเข้า (องศา decimal ตามตารางที่ 3)
   *  โหมดคอลัมน์เดียว (rOut ว่าง) อิง Type: T / C / SPIN / SPOUT
   *  โหมด rIn,rOut ชัดเจน -> compound spiral (R1->R2)
   *  trans = ชนิด transition: CLOTHOID(default) / BLOSS / COSINE / SINE  (มีผลเฉพาะ spiral)
   */
  function makeElement(type, staStart, staEnd, n, e, azDeg, rIn, rOut, trans) {
    var t = String(type).trim().toUpperCase();
    var kIn, kOut;
    if (rOut === undefined || rOut === null || rOut === '') {
      var k = curvatureFromRadius(rIn);
      if (t === 'SPIN')       { kIn = 0; kOut = k; }
      else if (t === 'SPOUT') { kIn = k; kOut = 0; }
      else                    { kIn = k; kOut = k; }   // T หรือ C
    } else {
      kIn = curvatureFromRadius(rIn);
      kOut = curvatureFromRadius(rOut);
    }
    var tr = trans ? String(trans).trim().toUpperCase() : 'CLOTHOID';
    return {
      type: t,
      staStart: staStart, staEnd: staEnd,
      n: n, e: e,
      az: FPMath.degToRad(azDeg),
      kIn: kIn, kOut: kOut,
      trans: tr
    };
  }

  /**
   * หาสถานะ { n, e, az } ที่ระยะ d จากต้น element
   *  (az = ทิศทาง tangent ณ จุดนั้น ใช้ต่อ offset)
   */
  function pointOnElement(el, d) {
    // --- Tangent: ความโค้ง 0 ทั้งคู่ -> เดินตรงตาม azimuth ---
    if (el.kIn === 0 && el.kOut === 0) {
      var pt = WCB.forwardCompute(el.n, el.e, el.az, d);
      return { n: pt.n, e: pt.e, az: el.az };
    }
    // --- Circular: ความโค้งคงที่ (เข้า=ออก, ไม่ใช่ 0) ---
    if (el.kIn === el.kOut) {
      var k = el.kIn;
      var theta = k * d;                                   // มุมเลี้ยวสะสม (signed)
      var chordLen = 2 / Math.abs(k) * Math.abs(Math.sin(theta / 2)); // ความยาวคอร์ด
      var chordAz = el.az + theta / 2;                     // คอร์ดแบ่งครึ่งมุมเลี้ยว
      var pc = WCB.forwardCompute(el.n, el.e, chordAz, chordLen);
      return { n: pc.n, e: pc.e, az: FPMath.normalizeAngle(el.az + theta) };
    }
    // --- COSINE (Civil 3D Sine Half-Wave) pure SPIN/SPOUT: closed form ---
    //  NEW — mirrors src/smt/alignment.py calculate_point_on_element:378-401
    //  and reference/vba/SMT_Alignment.bas:250-279. Bypasses the generic
    //  Simpson path below entirely for this case. shapeIntegral_/thetaAt_
    //  above stay as the fallback for compound COSINE (kIn and kOut both
    //  nonzero and unequal), which this branch does not cover.
    if (el.trans === 'COSINE' && (el.kIn === 0) !== (el.kOut === 0)) {
      var lenEl = el.staEnd - el.staStart;
      var xLocal, yLocal, thLocal;
      if (el.kIn === 0) {
        // SPIN: curvature 0 -> 1/R, canonical form used directly
        var rSpin = radiusFromCurvature(el.kOut);
        var bigXSpin = calcSineHalfwaveTangentLength(lenEl, rSpin);
        var ptSpin = sineHalfwavePoint_(d, bigXSpin, rSpin, lenEl);
        xLocal = ptSpin.x; yLocal = ptSpin.y; thLocal = ptSpin.theta;
      } else {
        // SPOUT: curvature 1/R -> 0, mirror canonical form via s <-> L-d
        var rSpout = radiusFromCurvature(el.kIn);
        var bigXSpout = calcSineHalfwaveTangentLength(lenEl, rSpout);
        var ptEnd = sineHalfwavePoint_(lenEl, bigXSpout, rSpout, lenEl);
        var ptG = sineHalfwavePoint_(lenEl - d, bigXSpout, rSpout, lenEl);
        var dxS = ptEnd.x - ptG.x, dyS = ptEnd.y - ptG.y;
        xLocal = dxS * Math.cos(ptEnd.theta) + dyS * Math.sin(ptEnd.theta);
        yLocal = dxS * Math.sin(ptEnd.theta) - dyS * Math.cos(ptEnd.theta);
        thLocal = ptEnd.theta - ptG.theta;
      }
      var caC = Math.cos(el.az), saC = Math.sin(el.az);
      return {
        n: el.n + xLocal * caC - yLocal * saC,
        e: el.e + xLocal * saC + yLocal * caC,
        az: FPMath.normalizeAngle(el.az + thLocal)
      };
    }
    // --- Spiral: ความโค้งเปลี่ยน (kIn != kOut) — รูปร่างตาม el.trans ---
    //  θ(s) มาจาก thetaAt_ (เลือกสูตรตามชนิด transition: CLOTHOID/BLOSS/COSINE/SINE)
    //  พิกัดท้องถิ่น (แกน x ตามทิศเข้า): x=∫cosθ ds, y=∫sinθ ds  (Simpson)
    var nSeg = SPIRAL_STEPS;                       // จำนวนช่วง Simpson (คู่)
    var h = d / nSeg;
    var sumX = 0, sumY = 0;
    for (var i = 0; i <= nSeg; i++) {
      var s = i * h;
      var th = thetaAt_(el, s);                    // มุมเลี้ยวสะสม ณ ระยะ s
      var w = (i === 0 || i === nSeg) ? 1 : (i % 2 === 1 ? 4 : 2);  // น้ำหนัก Simpson
      sumX += w * Math.cos(th);
      sumY += w * Math.sin(th);
    }
    var x = sumX * h / 3, y = sumY * h / 3;        // ระยะตามทิศเข้า / ตั้งฉาก
    var ca = Math.cos(el.az), sa = Math.sin(el.az);
    return {
      n: el.n + x * ca - y * sa,                   // หมุนกลับเข้าระบบ N,E
      e: el.e + x * sa + y * ca,
      az: FPMath.normalizeAngle(el.az + thetaAt_(el, d))   // มุมเลี้ยว ณ ระยะ d
    };
  }

  /** สถานะปลาย element — ใช้เชื่อมลูกโซ่และตรวจสอบ */
  function exitState(el) {
    return pointOnElement(el, el.staEnd - el.staStart);
  }

  /** หา index ของ element ที่ครอบ station นี้ (-1 ถ้าไม่เจอ) */
  function findElementIndex(elements, sta) {
    for (var i = 0; i < elements.length; i++) {
      if (FPMath.inRange(sta, elements[i].staStart, elements[i].staEnd, 1e-4)) return i;
    }
    return -1;
  }

  /**
   * *** ฟังก์ชันหัวใจ: station + offset -> พิกัด { n, e } ***
   *  offset: + = ขวามือของทิศเดินทาง, - = ซ้ายมือ, 0 = บน center line
   */
  function stationToCoord(elements, sta, offset) {
    if (offset === undefined) offset = 0;
    var i = findElementIndex(elements, sta);
    if (i < 0) throw new Error('station ' + sta + ' อยู่นอกแนวเส้นทาง');
    var st = pointOnElement(elements[i], sta - elements[i].staStart);
    if (!offset) return { n: st.n, e: st.e };
    var offAz = FPMath.normalizeAngle(st.az + Math.PI / 2);    // ขวามือ = +90°
    var p = WCB.forwardCompute(st.n, st.e, offAz, offset);
    return { n: p.n, e: p.e };
  }

  /**
   * ตรวจ Tangency Continuity: Exit(n) ต้อง = Entry(n+1)
   *  คืนลิสต์รอยต่อที่ผิดปกติ (gap เกิน tol หรือมุมต่างเกิน 5 ฟิลิปดา)
   */
  function validateChain(elements, tol) {
    if (tol === undefined) tol = 0.005;        // 5 มม.
    var issues = [];
    for (var i = 0; i < elements.length - 1; i++) {
      var a = elements[i], b = elements[i + 1];
      var ex = exitState(a);
      var gap = Math.hypot(ex.n - b.n, ex.e - b.e);
      var dAz = Math.abs(FPMath.radToDeg(FPMath.angleDiff(ex.az, b.az)) * 3600);
      if (gap > tol || dAz > 5) {
        issues.push({ between: (i + 1) + '->' + (i + 2), gap_mm: gap * 1000, az_arcsec: dAz });
      }
    }
    return issues;
  }

  /**
   * โปรเจกต์จุด P(pn,pe) ลงบน element เดียว -> { sta, offset, d, inRange }
   *  offset: + = ขวามือของทิศเดินทาง (ตรงกับ stationToCoord)
   */
  function projectToElement(el, pn, pe) {
    var L = el.staEnd - el.staStart;
    // --- Tangent: หาเท้าตั้งฉากบนเส้นตรง (dot product) ---
    if (el.kIn === 0 && el.kOut === 0) {
      var dN = pn - el.n, dE = pe - el.e;
      var cosA = Math.cos(el.az), sinA = Math.sin(el.az);
      var d = dN * cosA + dE * sinA;             // ระยะตามแนว (along)
      var offset = -dN * sinA + dE * cosA;       // ระยะตั้งฉาก (+ ขวา)
      return { sta: el.staStart + d, offset: offset, d: d,
               inRange: FPMath.inRange(d, 0, L, 1e-4) };
    }
    // --- Circular: เทียบมุมรอบจุดศูนย์กลางโค้ง ---
    if (el.kIn === el.kOut) {
      var k = el.kIn, R = 1 / k;
      var cn = el.n - R * Math.sin(el.az);       // จุดศูนย์กลางโค้ง
      var ce = el.e + R * Math.cos(el.az);
      var rho = Math.hypot(pn - cn, pe - ce);    // ระยะจากศูนย์กลางถึง P
      var phi0 = Math.atan2(el.e - ce, el.n - cn);
      var phiP = Math.atan2(pe - ce, pn - cn);
      var dC = FPMath.angleDiff(phiP, phi0) / k; // มุมที่กวาด -> ระยะตามโค้ง
      var offC = (k > 0 ? 1 : -1) * (Math.abs(R) - rho);
      return { sta: el.staStart + dC, offset: offC, d: dC,
               inRange: FPMath.inRange(dC, 0, L, 1e-4) };
    }
    // --- Spiral: หาเท้าตั้งฉากด้วย bisection ---
    //  หา s ที่เวกเตอร์ (P - จุดบนเส้น) ตั้งฉากกับ tangent  =>  g(s)=0
    var Ls = el.staEnd - el.staStart;
    function g(s) {
      var q = pointOnElement(el, s);
      return (pn - q.n) * Math.cos(q.az) + (pe - q.e) * Math.sin(q.az);
    }
    var g0 = g(0), gL = g(Ls);
    var inR = (g0 === 0) || (gL === 0) || ((g0 > 0) !== (gL > 0));  // g เปลี่ยนเครื่องหมาย?
    var sStar;
    if (inR) {
      var lo = 0, hi = Ls, gLo = g0;
      for (var it = 0; it < 50; it++) {
        var mid = (lo + hi) / 2, gm = g(mid);
        if ((gLo > 0) === (gm > 0)) { lo = mid; gLo = gm; } else { hi = mid; }
      }
      sStar = (lo + hi) / 2;
    } else {
      sStar = (Math.abs(g0) < Math.abs(gL)) ? 0 : Ls;   // เท้าตกนอกช่วง
    }
    var qs = pointOnElement(el, sStar);
    var offS = -(pn - qs.n) * Math.sin(qs.az) + (pe - qs.e) * Math.cos(qs.az);
    return { sta: el.staStart + sStar, offset: offS, d: sStar, inRange: inR };
  }

  /**
   * *** Inverse: พิกัด N,E -> { sta, offset } ***
   *  วนทุก element เลือกตัวที่จุดตกตั้งฉากได้จริง และ |offset| น้อยที่สุด
   */
  function coordToStation(elements, pn, pe) {
    var best = null;
    for (var i = 0; i < elements.length; i++) {
      var pr = projectToElement(elements[i], pn, pe);
      if (!pr || !pr.inRange) continue;
      if (best === null || Math.abs(pr.offset) < Math.abs(best.offset)) best = pr;
    }
    if (best === null) {
      throw new Error('จุดนี้ตกนอกทุก element (หรืออยู่ในช่วง spiral ของ Phase 1a)');
    }
    return { sta: best.sta, offset: best.offset };
  }

  return {
    curvatureFromRadius: curvatureFromRadius,
    radiusFromCurvature: radiusFromCurvature,
    calcSineHalfwaveTangentLength: calcSineHalfwaveTangentLength,   // NEW
    makeElement: makeElement,
    pointOnElement: pointOnElement,
    exitState: exitState,
    findElementIndex: findElementIndex,
    stationToCoord: stationToCoord,
    coordToStation: coordToStation,
    projectToElement: projectToElement,
    validateChain: validateChain,
    cosineCacheSize_: cosineCacheSize_   // NEW — debug/testing only, not part of the public API surface
  };
})();

if (typeof module !== 'undefined' && module.exports) module.exports = GS_Alignment;

// ============================================================
// Google Sheets custom-function (UDF) wrappers — NEW
// GS_Alignment above is an IIFE module; Sheets cells cannot call
// GS_Alignment.foo(...) directly, so these thin global wrappers exist
// purely for manual verification from a real spreadsheet (Phase 5 of
// session_logs/plan_20260713_0257.md §5). Mirrors the role VBA's
// `Public Function` already plays for the same purpose in
// reference/vba/SMT_Alignment.bas.
// ============================================================

/**
 * Closed-form tangent-projected length X for a COSINE spiral.
 * @param {number} length Element arc length L (m).
 * @param {number} r Radius at the curved end (m); sign does not matter.
 * @return {number} X (m).
 * @customfunction
 */
function GS_COSINE_TANGENT_LENGTH(length, r) {
  return GS_Alignment.calcSineHalfwaveTangentLength(length, r);
}

/**
 * Total turning angle (degrees) of a full-length COSINE SPIN(0->1/R).
 * @param {number} length Element arc length L (m).
 * @param {number} r Radius at the curved end (m).
 * @return {number} theta in decimal degrees.
 * @customfunction
 */
function GS_COSINE_THETA_DEG(length, r) {
  var el = GS_Alignment.makeElement('SPIN', 0, length, 0, 0, 0, r, null, 'COSINE');
  var st = GS_Alignment.exitState(el);
  return st.az * 180 / Math.PI;
}

/**
 * Local perpendicular offset y at the full-length end of a COSINE SPIN(0->1/R).
 * @param {number} length Element arc length L (m).
 * @param {number} r Radius at the curved end (m).
 * @return {number} y (m).
 * @customfunction
 */
function GS_COSINE_TOTAL_Y(length, r) {
  var el = GS_Alignment.makeElement('SPIN', 0, length, 0, 0, 0, r, null, 'COSINE');
  var st = GS_Alignment.exitState(el);
  // az=0, n=0, e=0 -> rotation is identity, so st.e IS the local y directly.
  return st.e;
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports.GS_COSINE_TANGENT_LENGTH = GS_COSINE_TANGENT_LENGTH;
  module.exports.GS_COSINE_THETA_DEG = GS_COSINE_THETA_DEG;
  module.exports.GS_COSINE_TOTAL_Y = GS_COSINE_TOTAL_Y;
}

// ============================================================
// Expected values -- verified in a real Google Sheets spreadsheet (not just
// Node smoke-test) against the same 3 ground-truth points used by
// reference/gsheet/smoke_test.js and VBA reference/vba/SMT_Alignment.bas:656-680.
// Confirmed 2026-07-13, all 9 values matched the plan's predicted values
// exactly, both before and after fixing the FPMath/WCB dependency setup in
// the Sheets project:
//
//   =GS_COSINE_TANGENT_LENGTH(100, 900) = 99.972013648519
//   =GS_COSINE_THETA_DEG(100, 900)      = 3.178942026889
//   =GS_COSINE_TOTAL_Y(100, 900)        = 1.651062316116
//
//   =GS_COSINE_TANGENT_LENGTH(50, 250)  = 49.954662110600
//   =GS_COSINE_THETA_DEG(50, 250)       = 5.705449190907
//   =GS_COSINE_TOTAL_Y(50, 250)         = 1.48409307253539
//
//   =GS_COSINE_TANGENT_LENGTH(70, 500)  = 69.968898207872
//   =GS_COSINE_THETA_DEG(70, 500)       = 4.002399624674
//   =GS_COSINE_TOTAL_Y(70, 500)         = 1.455757918206
// ============================================================
```

---

## FILE: reference/gsheet/GS_AlignmentBuilder.gs
```gs
/**
 * EXT-001: no-curve PI support — mirrors Python alignment_builder.py (commit cdf896d)
 *
 * ============================================================================
 *  GS_AlignmentBuilder — สร้างตาราง element จากเส้นโครง PI (แนว B)   [v2.0]
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
 *  EXT-003: ไฟล์นี้จะพอร์ต spiralTurningAngle_ (มุมเลี้ยว spiral จริง แทนสูตรเชิงเส้น
 *  Ls/(2R) เดิมใน curveSubs_) mirror src/smt/builders/alignment_builder.py:139-150
 *  (commit ba5de3c) ให้ COSINE ได้มุมเลี้ยวถูกต้อง — เทียบเท่า VBA Phase 4
 *  (reference/vba/SMT_Alignment.bas, commit e285fd5) ที่พอร์ตส่วนเดียวกันไปแล้ว ดู
 *  session_logs/plan_20260713_0257.md §2 — curveSubs_ patch เสร็จสมบูรณ์แล้ว (spiralTurningAngle_
 *  ใช้งานจริงในบรรทัด 45-49, 76-77 ด้านล่าง) ยืนยันผ่านครบทุกชั้น: Node-vs-Python (diff=0
 *  ทั้ง COSINE R=900/L=100, R=250/L=50, CLOTHOID R=500/L=80), `node
 *  reference/gsheet/smoke_test.js` (23/23), `pytest -q` (493 passed, ไม่ regression) ยืนยัน
 *  2026-07-13 — Group A (GS_Alignment.gs UDF 9 ค่า) และ Group B (COSINE ผ่าน buildFromPI)
 *  ผ่านการทดสอบพิมพ์สูตรจริงในเซลล์ Google Sheets แล้ว; Group C (CLOTHOID ผ่าน buildFromPI,
 *  vertex เดียวกับ Group B) ผ่านเฉพาะ Node เปรียบเทียบ Python โดยตรง (diff=0 ทุก control
 *  point) ในเครื่องเท่านั้น — ยังไม่เคยทดสอบพิมพ์สูตรในเซลล์ Sheets จริง
 *
 *  สร้างบน FPMath, WCB, GS_Alignment (ใช้ public API)
 * ============================================================================
 */
if (typeof FPMath === 'undefined' && typeof require !== 'undefined')       { var FPMath = require('../FPMath.gs'); }
if (typeof WCB === 'undefined' && typeof require !== 'undefined')          { var WCB = require('../WCB.gs'); }
if (typeof GS_Alignment === 'undefined' && typeof require !== 'undefined') { var GS_Alignment = require('./GS_Alignment.gs'); }

var GS_AlignmentBuilder = (function () {
  'use strict';

  // แตกโครงสร้างโค้งที่ PI ออกเป็นรายการ sub-element (kind, R, len, trans)
  // absD = มุมเลี้ยวรวม (รัศมีบวก), คืน {subs, issue}
  // EXT-003: มุมเลี้ยว spiral จริง (แทนสูตรเชิงเส้น Ls/(2R)) mirror
  // _spiral_turning_angle (src/smt/builders/alignment_builder.py:139-150, commit ba5de3c)
  function spiralTurningAngle_(R, length, trans) {
    var el = GS_Alignment.makeElement('SPIN', 0, length, 0, 0, 0, R, null, trans);
    var exit = GS_Alignment.exitState(el);
    return exit.az - el.az;
  }

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
      var thIn  = LsIn  > 0 ? spiralTurningAngle_(R, LsIn,  vert.transIn  || vert.trans) : 0;
      var thOut = LsOut > 0 ? spiralTurningAngle_(R, LsOut, vert.transOut || vert.trans) : 0;
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
      var el = GS_Alignment.makeElement(s.kind, sta, sta + s.len, cur.n, cur.e,
                                     FPMath.radToDeg(cur.az), sgn * s.R, undefined, s.trans);
      cur = GS_Alignment.exitState(el);
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
        els.push(GS_Alignment.makeElement('T', prev.sta, staPi, prev.n, prev.e,
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
      els.push(GS_Alignment.makeElement('T', prev.sta, staCS, prev.n, prev.e, FPMath.radToDeg(azIn), 0));
      control.push({ name: nm.start, sta: staCS, n: curveStart.n, e: curveStart.e });

      // ส่งทอดสร้าง sub-element จริง พร้อมจุด control
      var cur = { n: curveStart.n, e: curveStart.e, az: azIn }, sta = staCS;
      for (var i = 0; i < subs.length; i++) {
        var s = subs[i];
        var el = GS_Alignment.makeElement(s.kind, sta, sta + s.len, cur.n, cur.e,
                                       FPMath.radToDeg(cur.az), sgn * s.R, undefined, s.trans);
        els.push(el);
        cur = GS_Alignment.exitState(el);
        sta += s.len;
        var ptName = (i < subs.length - 1) ? nm.jct[i] : nm.end;
        control.push({ name: ptName, sta: sta, n: cur.n, e: cur.e });
      }
      prev = { n: cur.n, e: cur.e, sta: sta };
    }

    var ep = vertices[N - 1];
    var azEnd = WCB.azimuthFromCoords(prev.n, prev.e, ep.n, ep.e);
    var endLen = WCB.distance2D(prev.n, prev.e, ep.n, ep.e);
    els.push(GS_Alignment.makeElement('T', prev.sta, prev.sta + endLen, prev.n, prev.e, FPMath.radToDeg(azEnd), 0));
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

if (typeof module !== 'undefined' && module.exports) module.exports = GS_AlignmentBuilder;
```

---

## FILE: reference/gsheet/GS_TableSplitter.gs
```gs
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
```

---

## FILE: reference/gsheet/GS_PiTableParser.gs
```gs
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

    function flushPending_() {
      if (pendingPi === null) return;
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
```

---

## FILE: reference/gsheet/GS_ElementTable.gs
```gs
/**
 * GS_ElementTable — flattens GS_AlignmentBuilder.buildFromPI()'s `elements`
 * array into Table-1 rows for Sheet export.
 * Mirrors src/smt/cli.py::_run_build (lines 118-168) and
 * _radius_from_element() (lines 109-115).
 *
 * Columns: StaStart, StaEnd, N, E, Azimuth (deg), Radius, Type, Transition
 * Cells are real numbers (not .6f-formatted strings) per 2026-07-25 decision —
 * easier to sort/sum/use in Sheet formulas; decimal display is a Sheet
 * number-format concern, not this function's.
 * Transition is blanked to '' for T/C elements (only SPIN/SPOUT show it),
 * mirroring _run_build's `'' if el.type in ('T','C') else el.transition`.
 */
if (typeof FPMath === 'undefined' && typeof require !== 'undefined') { var FPMath = require('../FPMath.gs'); }

var GS_ElementTable = (function () {
  'use strict';

  var HEADER = ['StaStart', 'StaEnd', 'N', 'E', 'Azimuth', 'Radius', 'Type', 'Transition'];

  // mirrors _radius_from_element(el): signed design radius, 0 = tangent
  function radiusFromElement_(el) {
    if (el.kIn !== 0) return 1.0 / el.kIn;
    if (el.kOut !== 0) return 1.0 / el.kOut;
    return 0.0;
  }

  // elements -> array of row arrays (header NOT included; caller prepends HEADER)
  function elementsToRows(elements) {
    var rows = [];
    for (var i = 0; i < elements.length; i++) {
      var el = elements[i];
      var transitionVal = (el.type === 'T' || el.type === 'C') ? '' : el.trans;
      rows.push([
        el.staStart,
        el.staEnd,
        el.n,
        el.e,
        FPMath.radToDeg(el.az),
        radiusFromElement_(el),
        el.type,
        transitionVal,
      ]);
    }
    return rows;
  }

  return { HEADER: HEADER, elementsToRows: elementsToRows, radiusFromElement_: radiusFromElement_ };
})();

if (typeof module !== 'undefined' && module.exports) module.exports = GS_ElementTable;
```

---

## FILE: reference/gsheet/GS_CrossCheck.gs
```gs
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
```
