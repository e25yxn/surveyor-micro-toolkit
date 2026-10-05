/**
 * Node verification for the CUBIC (cubic parabola) transition in reference/gsheet/GS_Alignment.gs
 * and its use through GS_AlignmentBuilder.gs.
 * -----------------------------------------------------------------------
 * The GOLDEN values below were produced by the Python engine (src/smt/alignment.py and
 * src/smt/builders/alignment_builder.py, which are the authority for CUBIC); this script checks that
 * the Apps Script port reproduces them, that unknown transition names throw instead of silently
 * becoming CLOTHOID, and that a CUBIC spiral between two curved ends throws.
 *
 * Run:  node reference/gsheet/verify_cubic_transition.js
 * Exit code 0 = all checks passed; non-zero = at least one failure.
 */
'use strict';

var GS = require('./GS_Alignment.gs');
var GB = require('./GS_AlignmentBuilder.gs');
var G = {"tangentLengths": [[2500, 95, 94.99657129028134], [500, 100, 99.90063301583018], [300, 100, 99.72702863290004], [150, 60, 59.765915296731976], [1000, 100, 99.97503983512235], [5000, 50, 49.99987500198078], [-2500, 95, 94.99657129028134]], "start": [100.0, -50.0, 37.0], "points": [["SPIN", 300, 100, 0.0, 100.0, -50.0, 0.6457718232379017], ["SPIN", 300, 100, 10.0, 107.9830094680355, -43.97741457993783, 0.6474384874354397], ["SPIN", 300, 100, 35.0, 127.80774692509725, -28.747145208421408, 0.6661839528836975], ["SPIN", 300, 100, 77.0, 159.91331671284698, -1.6855295428990646, 0.744078874541243], ["SPIN", 300, 100, 100.0, 176.32943462328188, 14.417852977258098, 0.8100362663733334], ["SPOUT", 300, 100, 0.0, 100.0, -50.0, 0.6457718232379017], ["SPOUT", 300, 100, 10.0, 107.89176706236371, -43.858971534736526, 0.6763248725046447], ["SPOUT", 300, 100, 35.0, 126.85312391783631, -27.5722730274936, 0.739804893692904], ["SPOUT", 300, 100, 77.0, 156.84340916305635, 1.8219354567839714, 0.8012199651987499], ["SPOUT", 300, 100, 100.0, 172.7501040382686, 18.434382692697667, 0.8100362663733334], ["SPIN", -300, 100, 0.0, 100.0, -50.0, 0.6457718232379017], ["SPIN", -300, 100, 10.0, 107.98969629605372, -43.98628830043248, 0.6441051590403646], ["SPIN", -300, 100, 35.0, 128.09440907414574, -29.12755872887081, 0.6253596935921069], ["SPIN", -300, 100, 77.0, 162.9571980069102, -5.724896451812921, 0.5474647719345604], ["SPIN", -300, 100, 100.0, 182.96165813219233, 5.616595113929344, 0.48150738010247096], ["SPOUT", -300, 100, 0.0, 100.0, -50.0, 0.6457718232379017], ["SPOUT", -300, 100, 10.0, 108.07840124311828, -44.10664345784424, 0.6152187739711588], ["SPOUT", -300, 100, 35.0, 128.9606389377717, -30.369039921186086, 0.5517387527829003], ["SPOUT", -300, 100, 77.0, 165.4826085613229, -9.642669367631793, 0.4903236812770544], ["SPOUT", -300, 100, 100.0, 185.83599708019443, 1.0688160951314103, 0.48150738010247096], ["SPIN", 2500, 95, 0.0, 100.0, -50.0, 0.6457718232379017], ["SPIN", 2500, 95, 9.5, 107.58667522602506, -44.282276788334784, 0.6459618232342441], ["SPIN", 2500, 95, 33.25, 126.53909165285772, -29.9690593861006, 0.648099316513318], ["SPIN", 2500, 95, 73.15, 158.25414558127116, -5.7584282702159975, 0.6570361608985564], ["SPIN", 2500, 95, 95.0, 175.50558233034442, 7.650824090018024, 0.6647681664354055], ["SPOUT", 2500, 95, 0.0, 100.0, -50.0, 0.6457718232379017], ["SPOUT", 2500, 95, 9.5, 107.57652511146561, -44.268842237869706, 0.6493801100533698], ["SPOUT", 2500, 95, 33.25, 126.43654127478646, -29.834170816662663, 0.6567409423098507], ["SPOUT", 2500, 95, 73.15, 157.93732701834642, -5.345319143724475, 0.6637630669769399], ["SPOUT", 2500, 95, 95.0, 175.13909815716846, 8.12767335297383, 0.6647681664354055], ["SPIN", -500, 70, 0.0, 100.0, -50.0, 0.6457718232379017], ["SPIN", -500, 70, 7.0, 105.59143126079243, -45.78859948216616, 0.6450718234208352], ["SPIN", -500, 70, 24.5, 119.60856980362044, -35.31156689027532, 0.637197159493045], ["SPIN", -500, 70, 53.9, 143.4875715395588, -18.16296317673864, 0.6043068845566761], ["SPIN", -500, 70, 70.0, 156.8587026566012, -9.196053692575322, 0.5759538580707044], ["SPOUT", -500, 70, 0.0, 100.0, -50.0, 0.6457718232379017], ["SPOUT", -500, 70, 7.0, 105.61859232500387, -45.82499017682932, 0.6325569537202096], ["SPOUT", -500, 70, 24.5, 119.87811861443866, -35.68116384592821, 0.6055150735963206], ["SPOUT", -500, 70, 53.9, 144.29838184080756, -19.311623740694202, 0.5796568309903796], ["SPOUT", -500, 70, 70.0, 157.79017815624303, -10.526345358952705, 0.5759538580707044]], "builder": {"right_80_120": {"vertices": [{"n": 0.0, "e": 0.0, "sta": 0.0}, {"n": 1000.0, "e": 0.0, "R": 400.0, "LsIn": 80.0, "LsOut": 120.0, "trans": "CUBIC"}, {"n": 1612.8355544951824, "e": 514.2300877492314}], "control": [["BP", 0.0, 0.0, 0.0], ["TS", 812.5792357107878, 812.5792357107878, 0.0], ["SC", 892.5792357107878, 892.4997421234519, 2.6587252043547696], ["CS", 1072.747221693889, 1061.8145763793693, 59.649023032885395], ["ST", 1192.747221693889, 1157.3671064401876, 132.04668097339743], ["EP", 1787.3190538457393, 1612.8355544951824, 514.2300877492314]], "elements": [["T", 0.0, 812.5792357107878, ""], ["SPIN", 812.5792357107878, 892.5792357107878, "CUBIC"], ["C", 892.5792357107878, 1072.747221693889, ""], ["SPOUT", 1072.747221693889, 1192.747221693889, "CUBIC"], ["T", 1192.747221693889, 1787.3190538457393, ""]]}, "left_95": {"vertices": [{"n": 0.0, "e": 0.0, "sta": 5000.0}, {"n": 0.0, "e": 900.0, "R": 2500.0, "LsIn": 95.0, "LsOut": 95.0, "trans": "CUBIC"}, {"n": 295.8327832184896, "e": 1534.415450925655}], "control": [["BP", 5000.0, 0.0, 0.0], ["TS", 5298.221400239109, -3.6848311799627566e-14, 298.221400239109], ["SC", 5393.221400239109, 0.6016015235331628, 393.21797152939035], ["CS", 6389.0704667480495, 214.72057609914762, 1359.046250943011], ["ST", 6484.0704667480495, 254.3226257837016, 1445.3966310353114], ["EP", 6582.291866987154, 295.8327832184896, 1534.415450925655]], "elements": [["T", 5000.0, 5298.221400239109, ""], ["SPIN", 5298.221400239109, 5393.221400239109, "CUBIC"], ["C", 5393.221400239109, 6389.0704667480495, ""], ["SPOUT", 6389.0704667480495, 6484.0704667480495, "CUBIC"], ["T", 6484.0704667480495, 6582.291866987154, ""]]}, "two_curves": {"vertices": [{"n": 0.0, "e": 0.0, "sta": 0.0}, {"n": 800.0, "e": 0.0, "R": 600.0, "LsIn": 60.0, "LsOut": 60.0, "trans": "CUBIC"}, {"n": 1500.0, "e": 400.0, "R": 1200.0, "LsIn": 90.0, "LsOut": 70.0, "trans": "CUBIC"}, {"n": 2300.0, "e": 450.0}], "control": [["BP", 0.0, 0.0, 0.0], ["TS", 610.5572027257383, 610.5572027257383, 0.0], ["SC", 670.5572027257383, 670.5422266268117, 0.9992513819410698], ["CS", 922.124670219855, 911.9050564061853, 65.0966354030419], ["ST", 982.124670219855, 964.4824095582519, 93.98994831900102], ["TS", 1275.1621577320363, 1218.910198476085, 239.3772562720488], ["SC", 1365.1621577320363, 1297.5990235012182, 283.04712521302866], ["CS", 1833.2844910823965, 1743.7820694670852, 414.5546697846672], ["ST", 1903.2844910823965, 1813.5973688613549, 419.59983555383474], ["EP", 2390.63620142817, 2300.0, 450.0]], "elements": [["T", 0.0, 610.5572027257383, ""], ["SPIN", 610.5572027257383, 670.5572027257383, "CUBIC"], ["C", 670.5572027257383, 922.124670219855, ""], ["SPOUT", 922.124670219855, 982.124670219855, "CUBIC"], ["T", 982.124670219855, 1275.1621577320363, ""], ["SPIN", 1275.1621577320363, 1365.1621577320363, "CUBIC"], ["C", 1365.1621577320363, 1833.2844910823965, ""], ["SPOUT", 1833.2844910823965, 1903.2844910823965, "CUBIC"], ["T", 1903.2844910823965, 2390.63620142817, ""]]}}};

var pass = 0, failures = [];
function ok(cond, label, detail) {
  if (cond) { pass++; } else { failures.push(label + (detail ? ' :: ' + detail : '')); console.log('FAIL  ' + label + (detail ? ' :: ' + detail : '')); }
}
function close(a, b, tol, label) { ok(Math.abs(a - b) <= tol, label, 'actual=' + a + ' expected=' + b + ' diff=' + Math.abs(a - b).toExponential(3)); }
function throws(fn, label, mustContain) {
  var msg = null;
  try { fn(); } catch (e) { msg = String(e && e.message || e); }
  ok(msg !== null && (!mustContain || msg.indexOf(mustContain) >= 0), label, msg === null ? 'did not throw' : 'message=' + msg);
}

// 1) tangent-projected length X
G.tangentLengths.forEach(function (c) {
  close(GS.calcCubicParabolaTangentLength(c[1], c[0]), c[2], 1e-9, 'X  R=' + c[0] + ' L=' + c[1]);
});

// 2) points along SPIN / SPOUT (rotated, offset start; right and left turns)
G.points.forEach(function (p) {
  var el = GS.makeElement(p[0], 0, p[2], G.start[0], G.start[1], G.start[2], p[1], null, 'CUBIC');
  var st = GS.pointOnElement(el, p[3]);
  var lab = p[0] + ' R=' + p[1] + ' L=' + p[2] + ' d=' + p[3].toFixed(2);
  close(st.n, p[4], 1e-9, lab + ' n'); close(st.e, p[5], 1e-9, lab + ' e');
  var da = Math.abs(st.az - p[6]); da = Math.min(da, Math.abs(da - 2 * Math.PI));
  ok(da <= 1e-12, lab + ' az', 'actual=' + st.az + ' expected=' + p[6]);
});

// 3) builder parity: control points and element structure
Object.keys(G.builder).forEach(function (name) {
  var b = G.builder[name];
  var res = GB.buildFromPI(b.vertices);
  ok(res.issues.length === 0, name + ' no issues', JSON.stringify(res.issues));
  ok(res.control.length === b.control.length, name + ' control count', res.control.length + ' vs ' + b.control.length);
  b.control.forEach(function (c, i) {
    var r = res.control[i]; if (!r) return;
    ok(r.name === c[0], name + ' control[' + i + '] name', r.name + ' vs ' + c[0]);
    close(r.sta, c[1], 1e-7, name + ' ' + c[0] + ' sta'); close(r.n, c[2], 1e-7, name + ' ' + c[0] + ' n'); close(r.e, c[3], 1e-7, name + ' ' + c[0] + ' e');
  });
  ok(res.elements.length === b.elements.length, name + ' element count', res.elements.length + ' vs ' + b.elements.length);
  b.elements.forEach(function (e, i) {
    var r = res.elements[i]; if (!r) return;
    ok(r.type === e[0], name + ' element[' + i + '] type', r.type + ' vs ' + e[0]);
    if (e[3]) ok(r.trans === e[3], name + ' element[' + i + '] trans', r.trans + ' vs ' + e[3]);
  });
});

// 4) CUBIC really differs from CLOTHOID (guards against silently using the default branch)
(function () {
  var a = GS.exitState(GS.makeElement('SPIN', 0, 100, 0, 0, 0, 300, null, 'CUBIC'));
  var b = GS.exitState(GS.makeElement('SPIN', 0, 100, 0, 0, 0, 300, null, 'CLOTHOID'));
  ok(Math.abs(a.e - b.e) > 0.015 && Math.abs(a.az - b.az) > 1e-3, 'CUBIC differs from CLOTHOID at R=300', 'de=' + (a.e - b.e) + ' daz=' + (a.az - b.az));
  var r = GS.exitState(GS.makeElement('SPIN', 0, 95, 0, 0, 0, 2500, null, 'CUBIC'));
  var deficitArcsec = (95 / (2 * 2500) - r.az) * 206264.806;
  ok(deficitArcsec > 0.70 && deficitArcsec < 0.80, 'real-drawing pin: turning-angle deficit 0.70-0.80 arcsec (R=2500, L=95)', String(deficitArcsec));
})();

// 5) unknown transition names throw (SPIN/SPOUT only); known / blank names still accepted
['SPIN', 'SPOUT'].forEach(function (t) {
  ['CUBICC', 'COSIN', 'abcdef', 'LINEAR'].forEach(function (bad) {
    throws(function () { GS.makeElement(t, 0, 100, 0, 0, 0, 500, null, bad); }, t + ' rejects ' + bad, 'ไม่รู้จัก transition');
  });
});
['clothoid', ' Bloss ', 'SINE', 'cosine', 'Cubic', '', null, undefined].forEach(function (okName) {
  var el = GS.makeElement('SPIN', 0, 100, 0, 0, 0, 500, null, okName);
  ok(['CLOTHOID', 'BLOSS', 'SINE', 'COSINE', 'CUBIC'].indexOf(el.trans) >= 0, 'accepts ' + JSON.stringify(okName), el.trans);
});
['T', 'C'].forEach(function (t) {
  var threw = false; try { GS.makeElement(t, 0, 100, 0, 0, 0, t === 'T' ? 0 : 500, null, 'whatever'); } catch (e) { threw = true; }
  ok(!threw, t + ' element ignores an unused Transition value');
});

// 6) CUBIC between two curved ends throws instead of becoming a clothoid
throws(function () { GS.exitState(GS.makeElement('SPIN', 0, 100, 0, 0, 0, 500, 300, 'CUBIC')); }, 'compound CUBIC throws', 'CUBIC');

// 7) builder rejects a typo'd transition in a PI row
throws(function () {
  GB.buildFromPI([{ n: 0, e: 0, sta: 0 }, { n: 1000, e: 0, R: 400, LsIn: 80, LsOut: 80, trans: 'CUBICC' }, { n: 1600, e: 514 }]);
}, 'buildFromPI rejects a typo transition', 'ไม่รู้จัก transition');

console.log('\n' + pass + ' checks passed, ' + failures.length + ' failed');
if (failures.length) { console.log('FAILURES:\n  ' + failures.join('\n  ')); process.exit(1); }
