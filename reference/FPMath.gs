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
