/**
 * ============================================================================
 *  Alignment — Alignment Engine (Horizontal)   [Phase 1a: Tangent + Circular]
 * ----------------------------------------------------------------------------
 *  โมเดล: แนวเส้นทาง = ลิสต์ของ element ที่ต่อเรียงกัน (List of Elements)
 *  กฎเหล็ก (Point Forwarding): Exit State ของ element(n) = Entry State ของ element(n+1)
 *    => เก็บแค่ Entry State ต่อ element พอ, Exit คำนวณเอา (และใช้ตรวจสอบความต่อเนื่องได้)
 *
 *  แต่ละ element อธิบายด้วย "ความโค้ง" curvature (k = 1/R):
 *    Tangent      : kIn=0,    kOut=0
 *    Circular     : kIn=1/R,  kOut=1/R    (เท่ากัน)
 *    Spiral เข้า  : kIn=0,    kOut=1/R    (Phase 1b)
 *    Spiral ออก   : kIn=1/R,  kOut=0      (Phase 1b)
 *    Compound spiral: kIn=1/R1, kOut=1/R2 (Phase 1b)
 *  ใช้ curvature แทนรัศมีเพราะ tangent = 0 (เลี่ยงปัญหา R = อนันต์)
 *  เครื่องหมาย: k บวก = เลี้ยวขวา (azimuth เพิ่ม), k ลบ = เลี้ยวซ้าย
 *
 *  สร้างบน FPMath และ WCB
 * ============================================================================
 */
if (typeof FPMath === 'undefined' && typeof require !== 'undefined') { var FPMath = require('./FPMath.gs'); }
if (typeof WCB === 'undefined' && typeof require !== 'undefined')    { var WCB = require('./WCB.gs'); }

var Alignment = (function () {
  'use strict';

  var SPIRAL_STEPS = 48;   // จำนวนช่วง Simpson สำหรับ integrate spiral (คู่; 48 ละเอียดระดับไมครอน)

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
   *  ตรวจครบทุกชนิด element รวม spiral (Phase 1b คำนวณ spiral ได้แล้ว)
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
    makeElement: makeElement,
    pointOnElement: pointOnElement,
    exitState: exitState,
    findElementIndex: findElementIndex,
    stationToCoord: stationToCoord,
    coordToStation: coordToStation,
    projectToElement: projectToElement,
    validateChain: validateChain
  };
})();

if (typeof module !== 'undefined' && module.exports) module.exports = Alignment;
