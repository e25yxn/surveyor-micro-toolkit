/**
 * ============================================================================
 *  CrossFall — ความลาดขวาง / การยกโค้ง (Cross-fall / Superelevation) [Phase 2.2]
 * ----------------------------------------------------------------------------
 *  คำนวณ "cross-fall (%)" ณ สถานีใดๆ จากตารางแบบแบ่งช่วง (segment)
 *
 *  ตาราง X (เช่น Named Range "X_ROR4") — 1 แถว = 1 ช่วง:
 *    [index] | Sta.Start | Sta.End | X_Start | X_End | TYPE
 *      col0      col1        col2      col3      col4    col5
 *    - คอลัมน์แรก (index) ไม่ใช้ในการคำนวณ (เก็บไว้ได้ตามตารางเดิม)
 *    - TYPE:
 *        N = คงที่ (normal)                 -> ค่า = X_Start
 *        V = เชิงเส้น (linear, ค่าหลัก)      -> X1 + (X2-X1)*t
 *        S = S-curve นุ่ม (smoothstep/Bloss) -> X1 + (X2-X1)*(3t²-2t³)
 *      (t = สัดส่วนระยะในช่วง; ว่างหรือไม่ใช่ N/S = ใช้ V เป็นค่าตั้งต้น)
 *
 *  V กับ S ให้ค่าเท่ากันที่ปลายและกลางช่วง แต่ S ลาดเข้า-ออกนุ่มกว่า
 *  (อัตราเปลี่ยน cross-fall ที่ปลาย = 0 -> รถเอียงตัวนุ่มกว่า) — ตัวเลือกเสริม
 *
 *  เทียบเท่าสูตร VBA เดิม XFall() โดยเพิ่มทางเลือก S ที่เคย comment ไว้
 *  สร้างแบบ standalone (ไม่พึ่งไฟล์อื่น)
 * ============================================================================
 */
var CrossFall = (function () {
  'use strict';

  // cross-fall (%) ณ สถานี sta ภายใน 1 ช่วง
  //  seg = {staStart, staEnd, xStart, xEnd, type}
  function crossFallAt(seg, sta) {
    var x1 = seg.xStart, x2 = seg.xEnd;
    var type = String(seg.type || 'V').trim().toUpperCase();
    if (type === 'N' || x1 === x2) return x1;            // คงที่
    var L = seg.staEnd - seg.staStart;
    if (L === 0) return x1;
    var t = (sta - seg.staStart) / L;
    var f = (type === 'S') ? t * t * (3 - 2 * t)         // S-curve (Bloss smoothstep)
                           : t;                           // V (linear) — ค่าหลัก
    return x1 + (x2 - x1) * f;
  }

  // อัตราเปลี่ยน cross-fall (% ต่อเมตร) ณ สถานี — ไว้ตรวจความนุ่ม (roll rate)
  function rateAt(seg, sta) {
    var type = String(seg.type || 'V').trim().toUpperCase();
    var L = seg.staEnd - seg.staStart;
    if (type === 'N' || seg.xStart === seg.xEnd || L === 0) return 0;
    var t = (sta - seg.staStart) / L, dx = seg.xEnd - seg.xStart;
    var dfdt = (type === 'S') ? 6 * t * (1 - t) : 1;     // d/dt ของรูปร่าง
    return dx * dfdt / L;
  }

  function crossFallFromTable(segs, sta) {
    for (var i = 0; i < segs.length; i++) {
      var g = segs[i], last = (i === segs.length - 1);
      if (sta >= g.staStart && (sta < g.staEnd || (last && sta <= g.staEnd))) {
        return crossFallAt(g, sta);
      }
    }
    return null;
  }

  return { crossFallAt: crossFallAt, rateAt: rateAt, crossFallFromTable: crossFallFromTable };
})();

// ---- custom function สำหรับเรียกในเซลล์ (แทน VBA XFall) ----
function parseCrossFall_(table) {
  var segs = [];
  if (!table || !table.length) return segs;            // ว่าง/ไม่ได้ใส่ -> ตารางว่าง
  for (var i = 0; i < table.length; i++) {
    var r = table[i];
    if (r[1] === '' || r[1] === null || r[1] === undefined || isNaN(Number(r[1]))) continue;
    segs.push({
      staStart: Number(r[1]), staEnd: Number(r[2]),
      xStart: Number(r[3]), xEnd: Number(r[4]), type: r[5]
    });
  }
  return segs;
}

/** cross-fall (%) ณ สถานี.  =XFALL(X_ROR4, sta) */
function XFALL(xTable, sta) {
  if (sta === '' || sta === null || sta === undefined) return '';
  var v = CrossFall.crossFallFromTable(parseCrossFall_(xTable), Number(sta));
  return v === null ? '#STA_OUT' : v;
}

if (typeof module !== 'undefined' && module.exports) module.exports = CrossFall;
