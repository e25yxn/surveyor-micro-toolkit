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
