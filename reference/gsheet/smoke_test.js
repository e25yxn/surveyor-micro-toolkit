/**
 * Node smoke-test for reference/gsheet/GS_Alignment.gs
 * -----------------------------------------------------------------------
 * Lightweight standalone check (not Jest) per session_logs/plan_20260713_0257.md
 * §4 — verifies the COSINE closed-form + arc-length inversion port before
 * any Google Sheets deployment. Requires GS_Alignment.gs directly via
 * Node's CommonJS require() (confirmed working on a raw .gs path).
 *
 * Run:  node reference/gsheet/smoke_test.js
 * Exit code 0 = all checks passed; non-zero = at least one failure (see
 * printed FAIL lines and the FAILURES summary at the end).
 */
'use strict';

var GS = require('./GS_Alignment.gs');

var passCount = 0;
var failures = [];

function assertClose(actual, expected, tol, label) {
  var diff = Math.abs(actual - expected);
  if (diff <= tol) {
    passCount++;
    console.log('PASS  ' + label + '  actual=' + actual + '  expected=' + expected + '  diff=' + diff.toExponential(3));
  } else {
    failures.push(label + ': actual=' + actual + ' expected=' + expected + ' diff=' + diff + ' (tol=' + tol + ')');
    console.log('FAIL  ' + label + '  actual=' + actual + '  expected=' + expected + '  diff=' + diff.toExponential(3));
  }
}

function assertEqual(actual, expected, label) {
  if (actual === expected) {
    passCount++;
    console.log('PASS  ' + label + '  value=' + actual);
  } else {
    failures.push(label + ': actual=' + actual + ' expected=' + expected);
    console.log('FAIL  ' + label + '  actual=' + actual + '  expected=' + expected);
  }
}

var TOL = 1e-9;   // same absolute tolerance as tests/test_alignment.py's COSINE endpoint test

// ============================================================
// 1) COSINE closed-form endpoint — 3 ground-truth Civil 3D points
//    (same points used to verify Python tests/test_alignment.py and VBA
//    Phase 4 reference/vba/SMT_Alignment.bas "Expected values" comment):
//    R=900/L=100, R=250/L=50, R=500/L=70 — totalX, totalY, theta (9 values
//    total). totalX expected values computed independently via the plain
//    closed-form arithmetic X = L - 0.0226689447*L^3/R^2 (NOT by calling
//    GS.calcSineHalfwaveTangentLength itself, which would be circular);
//    R=250/L=50's X=49.9546621106 matches the independent Civil 3D XML
//    export ground truth in session_logs/investigate_sinehalfwave_formula.md
//    exactly. theta/totalY come from tests/test_alignment.py's
//    test_cosine_endpoint_matches_a1_closed_form parametrize table.
// ============================================================
console.log('\n--- 1) COSINE closed-form endpoint (3 ground-truth points x 3 metrics = 9 values) ---');

var groundTruth = [
  { r: 900.0, length: 100.0, thetaDeg: 3.1789420268894153, y: 1.6510623161163274, x: 99.97201364851851 },
  { r: 250.0, length: 50.0,  thetaDeg: 5.705449190907088,  y: 1.4840930725353705, x: 49.9546621106 },
  { r: 500.0, length: 70.0,  thetaDeg: 4.002399624673551,  y: 1.4557579182062208, x: 69.9688982078716 }
];

groundTruth.forEach(function (gt) {
  var label = 'R=' + gt.r + '/L=' + gt.length;

  var xActual = GS.calcSineHalfwaveTangentLength(gt.length, gt.r);
  assertClose(xActual, gt.x, TOL, label + ' totalX');

  var el = GS.makeElement('SPIN', 0, gt.length, 0, 0, 0, gt.r, null, 'COSINE');
  var st = GS.exitState(el);   // az=0, n=0, e=0 start -> st.n=x_local, st.e=y_local (identity rotation)
  var thetaDeg = st.az * 180 / Math.PI;
  assertClose(thetaDeg, gt.thetaDeg, TOL, label + ' theta_deg');
  assertClose(st.e, gt.y, TOL, label + ' totalY');
});

// ============================================================
// 2) SPIN/SPOUT symmetry — Civil 3D-confirmed invariant: SPIN and SPOUT
//    of equal R,L share the same total turning angle (theta). Mirrors
//    tests/test_alignment.py::test_cosine_spin_spout_symmetry_matches_civil3d
//    (lines 511-523) EXACTLY — that test asserts ONLY the turning-angle
//    match, not e/totalY.
//
//    e (local y at exitState) is NOT expected to match between SPIN and
//    SPOUT: el.az=0 represents the tangent at the CURVED end for SPOUT
//    (SPOUT starts curved, ends straight) but the ZERO-CURVATURE end for
//    SPIN, so exitState(...).e is measured in two different reference
//    frames. Confirmed this is expected engine behaviour, not a GS port
//    bug, by running the identical computation through the already
//    oracle-validated Python engine directly
//    (src/smt/alignment.py::calculate_point_on_element) -- it produces
//    the exact same "mismatched" e values GS_Alignment.gs does (e.g.
//    R=900/L=100 SPOUT e=3.8953806803844753 in both).
// ============================================================
console.log('\n--- 2) SPIN/SPOUT symmetry (3 ground-truth points, theta only) ---');

groundTruth.forEach(function (gt) {
  var label = 'R=' + gt.r + '/L=' + gt.length;
  var spinEl = GS.makeElement('SPIN', 0, gt.length, 0, 0, 0, gt.r, null, 'COSINE');
  var spoutEl = GS.makeElement('SPOUT', 0, gt.length, 0, 0, 0, gt.r, null, 'COSINE');
  var spinExit = GS.exitState(spinEl);
  var spoutExit = GS.exitState(spoutEl);
  assertClose(spoutExit.az, spinExit.az, TOL, label + ' SPIN/SPOUT theta match');
});

// ============================================================
// 3) Cache sharing — SPIN and SPOUT of equal length/|R| must share ONE
//    arc-length-table Map entry (mirrors Python's lru_cache assertion
//    test_cosine_arc_length_table_cached_across_spin_spout, info.currsize
//    == 1). Uses a mid-curve point (d = length/2) because d == length
//    takes the a=1 shortcut in sineHalfwavePoint_ and never touches the
//    cache/bisection path at all.
//
//    IMPORTANT: cacheR/cacheLength must NOT match any (length, |R|) pair
//    used elsewhere in this file. Test 2's SPOUT exitState() calls
//    internally evaluate sineHalfwavePoint_(lenEl - d, ...) at d=0 (not
//    d==length) to get ptG, which does NOT take the a=1 shortcut and so
//    DOES populate the cache for each ground-truth (length, |R|) pair as
//    a side effect. Reusing R=900/L=100 here would collide with that and
//    make sizeBefore already non-zero, causing a false assertEqual
//    failure unrelated to any real bug in GS_Alignment.gs -- use a
//    distinct pair to remove the test-ordering dependency entirely.
// ============================================================
console.log('\n--- 3) Cache sharing (SPIN then SPOUT, same length/|R|) ---');

var cacheR = 333.0, cacheLength = 44.0;
var sizeBefore = GS.cosineCacheSize_();

var spinElC = GS.makeElement('SPIN', 0, cacheLength, 0, 0, 0, cacheR, null, 'COSINE');
GS.pointOnElement(spinElC, cacheLength / 2);
var sizeAfterSpin = GS.cosineCacheSize_();
assertEqual(sizeAfterSpin, sizeBefore + 1, 'cache grows by exactly 1 after first SPIN mid-curve call');

var spoutElC = GS.makeElement('SPOUT', 0, cacheLength, 0, 0, 0, cacheR, null, 'COSINE');
GS.pointOnElement(spoutElC, cacheLength / 2);
var sizeAfterSpout = GS.cosineCacheSize_();
assertEqual(sizeAfterSpout, sizeAfterSpin, 'cache does NOT grow again for SPOUT of same length/|R| (shared table)');

// ============================================================
// 4) Regression — CLOTHOID/BLOSS/SINE must be numerically unaffected by
//    the new COSINE branch (it only triggers when el.trans === 'COSINE').
//    Expected values computed independently via the already
//    oracle-validated Python engine (src/smt/alignment.py
//    calculate_point_on_element), same R/L, SPIN, az=0/n=0/e=0 start:
//      python3 -c "from smt import alignment as al; ..." (see
//      session_logs/latest.md for the exact command used to generate
//      these literals).
// ============================================================
console.log('\n--- 4) Regression: CLOTHOID/BLOSS/SINE unaffected ---');

var regressionCases = [
  { trans: 'CLOTHOID', r: 500.0, length: 80.0, n: 79.94881516174787,  e: 2.132358292954413,  azDeg: 4.58366236104659 },
  { trans: 'BLOSS',    r: 500.0, length: 80.0, n: 79.9532840284633,   e: 1.9190977605777484, azDeg: 4.58366236104659 },
  { trans: 'SINE',     r: 500.0, length: 80.0, n: 79.95516036066282,  e: 1.8082297810023913, azDeg: 4.58366236104659 }
];

regressionCases.forEach(function (rc) {
  var label = rc.trans + ' R=' + rc.r + '/L=' + rc.length;
  var el = GS.makeElement('SPIN', 0, rc.length, 0, 0, 0, rc.r, null, rc.trans);
  var st = GS.exitState(el);
  assertClose(st.n, rc.n, TOL, label + ' n');
  assertClose(st.e, rc.e, TOL, label + ' e');
  assertClose(st.az * 180 / Math.PI, rc.azDeg, TOL, label + ' azDeg');
});

// ============================================================
console.log('\n============================================================');
console.log(passCount + ' passed, ' + failures.length + ' failed');
if (failures.length > 0) {
  console.log('\nFAILURES:');
  failures.forEach(function (f) { console.log('  - ' + f); });
  process.exit(1);
} else {
  console.log('ALL SMOKE TESTS PASSED');
  process.exit(0);
}
