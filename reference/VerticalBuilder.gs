/**
 * ============================================================================
 *  VerticalBuilder — สร้างตาราง V จากแนว VPI   [Phase 2.4]
 * ----------------------------------------------------------------------------
 *  ฝาแฝดของ AlignmentBuilder แต่อยู่ในระนาบ สถานี-ระดับ
 *    VPI ~ PI ,  เกรด(%) ~ azimuth ,  โค้งดิ่งพาราโบลา ~ โค้งวงกลม ,  LVC ~ ความยาวโค้ง
 *
 *  รับ: vpis = [ BVP, {VPI...}, ..., EVP ]
 *    - BVP (จุดแรก) / EVP (จุดท้าย): {sta, elev}   (ไม่มีโค้ง)
 *    - VPI กลาง:  {sta, elev, L}            โค้งสมมาตร (L = ความยาวรวม)
 *               หรือ {sta, elev, L1, L2}    โค้งอสมมาตร (สองกิ่ง)
 *    - เกรดคำนวณเองจากระดับ VPI ที่ต่อกัน (ไม่ต้องป้อน)
 *  คืน: { rows, control, issues }
 *    - rows = แถวตาราง V พร้อมใช้กับ VLEVEL: {staStart,staEnd,level,g1,g2,lvc,lvc2}
 *    - control = จุด PVC/PVI/PVT (ไว้ cross-check)
 *
 *  สร้างแบบ standalone (ไม่พึ่งไฟล์อื่น)
 * ============================================================================
 */
var VerticalBuilder = (function () {
  'use strict';

  function buildFromVPI(vpis) {
    var rows = [], control = [], issues = [];
    var N = vpis.length;
    var endSta = vpis[0].sta, endElev = vpis[0].elev;
    control.push({ name: 'BVP', sta: endSta, elev: endElev });

    for (var i = 1; i < N - 1; i++) {
      var v = vpis[i];
      var gIn  = (v.elev - vpis[i - 1].elev) / (v.sta - vpis[i - 1].sta) * 100;
      var gOut = (vpis[i + 1].elev - v.elev) / (vpis[i + 1].sta - v.sta) * 100;
      var sym = (v.L1 == null && v.L2 == null);
      var L1 = sym ? (v.L || 0) / 2 : (v.L1 != null ? v.L1 : 0);
      var L2 = sym ? (v.L || 0) / 2 : (v.L2 != null ? v.L2 : 0);

      var pvcSta = v.sta - L1, pvtSta = v.sta + L2;
      var pvcElev = v.elev - gIn * L1 / 100;
      var pvtElev = v.elev + gOut * L2 / 100;

      if (pvcSta > endSta + 1e-9) {                 // tangent grade ก่อนโค้ง
        rows.push({ staStart: endSta, staEnd: pvcSta, level: endElev, g1: gIn, g2: gIn, lvc: 0, lvc2: null });
      } else if (pvcSta < endSta - 1e-6) {
        issues.push('VPI#' + i + ' (STA ' + v.sta + '): โค้งดิ่งซ้อนกับช่วงก่อนหน้า (LVC ยาวเกิน)');
      }
      control.push({ name: 'PVC', sta: pvcSta, elev: pvcElev });

      rows.push({ staStart: pvcSta, staEnd: pvtSta, level: pvcElev, g1: gIn, g2: gOut,
                  lvc: sym ? (v.L || 0) : L1, lvc2: sym ? null : L2 });        // โค้งดิ่ง
      control.push({ name: 'PVI', sta: v.sta, elev: v.elev });
      control.push({ name: 'PVT', sta: pvtSta, elev: pvtElev });

      endSta = pvtSta; endElev = pvtElev;
    }

    var ep = vpis[N - 1];
    if (ep.sta > endSta + 1e-9) {                    // tangent ปลายสุด
      var gEnd = (ep.elev - endElev) / (ep.sta - endSta) * 100;
      rows.push({ staStart: endSta, staEnd: ep.sta, level: endElev, g1: gEnd, g2: gEnd, lvc: 0, lvc2: null });
    }
    control.push({ name: 'EVP', sta: ep.sta, elev: ep.elev });

    return { rows: rows, control: control, issues: issues };
  }

  // แปลง rows เป็นตาราง 2 มิติ พร้อมวางในชีต (คอลัมน์: StaStart..LVC2)
  function toTable(rows) {
    var out = [];
    for (var i = 0; i < rows.length; i++) {
      var r = rows[i];
      out.push([r.staStart, r.staEnd, r.level, r.g1, r.g2, r.lvc, (r.lvc2 == null ? '' : r.lvc2)]);
    }
    return out;
  }

  // cross-check: เทียบค่าจากแบบ (sta, elev) กับจุด control ที่คำนวณได้
  function crossCheck(control, drawing, tolSta, tolElev) {
    if (tolSta == null) tolSta = 0.01;
    if (tolElev == null) tolElev = 0.005;
    var report = [];
    for (var j = 0; j < drawing.length; j++) {
      var d = drawing[j];
      var best = null, bd = Infinity;
      for (var i = 0; i < control.length; i++) {
        var c = control[i];
        if (d.name && String(d.name).length && c.name !== d.name) continue;
        var dd = Math.abs(c.sta - d.sta);
        if (dd < bd) { bd = dd; best = c; }
      }
      if (!best) continue;
      var dSta = Math.abs(best.sta - d.sta), dElev = Math.abs(best.elev - d.elev);
      report.push({ name: d.name || best.name, sta: best.sta, dSta: dSta, dElev: dElev, ok: dSta <= tolSta && dElev <= tolElev });
    }
    return report;
  }

  return { buildFromVPI: buildFromVPI, toTable: toTable, crossCheck: crossCheck };
})();

if (typeof module !== 'undefined' && module.exports) module.exports = VerticalBuilder;
