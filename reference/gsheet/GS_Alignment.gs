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
