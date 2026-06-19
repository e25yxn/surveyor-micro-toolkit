/**
 * ============================================================================
 *  Vertical — โปรไฟล์ระดับ (Vertical Alignment)   [Phase 2.1]
 * ----------------------------------------------------------------------------
 *  คำนวณ "ระดับ (Level/Elevation)" ณ สถานีใดๆ จากตารางแบบแบ่งช่วง (segment)
 *  โครงสร้างขนานกับฝั่งราบ:  เกรด(%) ~ azimuth ,  โค้งดิ่งพาราโบลา ~ โค้งวงกลม
 *
 *  ตาราง V (เช่น Named Range "V_ROR4") — 1 แถว = 1 ช่วง:
 *    [index] | Sta.Start | Sta.End | Level | G1(%) | G2(%) | LVC | (LVC2)
 *      col0      col1        col2      col3   col4    col5    col6   col7
 *    - คอลัมน์แรก (index) ไม่ใช้ในการคำนวณ (เก็บไว้ได้ตามตารางเดิม)
 *    - LVC = 0  -> ช่วงเส้นเกรดตรง (tangent grade)
 *    - LVC > 0  -> โค้งดิ่งพาราโบลา (สมมาตร: LVC = ความยาวรวม)
 *    - ใส่ LVC2 (คอลัมน์ 8) เมื่อเป็นโค้งดิ่ง "อสมมาตร": LVC=L1, LVC2=L2 (สองกิ่ง)
 *
 *  เทียบเท่าสูตร VBA เดิม Ver()/VerticalCurve() แต่กิ่งอสมมาตรคิดเครื่องหมาย
 *  crest/sag ในสูตรเดียว (ค่า e มีเครื่องหมายตาม G2-G1 อยู่แล้ว)
 *
 *  สร้างแบบ standalone (ไม่พึ่งไฟล์อื่น)
 * ============================================================================
 */
var Vertical = (function () {
  'use strict';

  // ระดับ ณ สถานี sta ภายใน 1 ช่วง
  //  seg = {staStart, staEnd, level, g1, g2, lvc, lvc2}
  function levelAt(seg, sta) {
    var Lx = sta - seg.staStart;
    var base = seg.level + (seg.g1 / 100) * Lx;          // เส้นเกรดเข้า G1
    var L1 = seg.lvc;
    if (!L1) return base;                                 // tangent grade (LVC=0)

    var hasL2 = (seg.lvc2 != null && seg.lvc2 !== '');
    if (!hasL2) {                                         // โค้งสมมาตร (LVC = ความยาวรวม)
      return base + (seg.g2 - seg.g1) / (200 * L1) * Lx * Lx;
    }

    // โค้งอสมมาตร (unequal-tangent): L1=LVC, L2=LVC2 = ความยาวสองกิ่ง
    var L2 = seg.lvc2, Ltot = L1 + L2;
    var e = (L1 * L2) / (200 * Ltot) * (seg.g2 - seg.g1); // middle ordinate ที่ PVI (มีเครื่องหมาย)
    if (Lx <= L1) {
      return base + e * (Lx / L1) * (Lx / L1);            // กิ่งแรก PVC->PVI
    }
    var levPVT = seg.level + (seg.g1 / 100) * L1 + (seg.g2 / 100) * L2;
    var Lx2 = seg.staEnd - sta;
    return levPVT - (seg.g2 / 100) * Lx2 + e * (Lx2 / L2) * (Lx2 / L2);  // กิ่งสอง PVI->PVT
  }

  // เกรดชั่วขณะ (%) ณ สถานี sta — อนุพันธ์ของระดับ (ไว้ตรวจออกแบบ)
  function gradeAt(seg, sta) {
    var L1 = seg.lvc;
    if (!L1) return seg.g1;
    var Lx = sta - seg.staStart;
    var hasL2 = (seg.lvc2 != null && seg.lvc2 !== '');
    if (!hasL2) return seg.g1 + (seg.g2 - seg.g1) * (Lx / L1);   // สมมาตร (L1=รวม)
    var L2 = seg.lvc2, Ltot = L1 + L2;
    var e = (L1 * L2) / (200 * Ltot) * (seg.g2 - seg.g1);
    if (Lx <= L1) return seg.g1 + 200 * e * Lx / (L1 * L1);      // กิ่งแรก
    var Lx2 = seg.staEnd - sta;
    return seg.g2 - 200 * e * Lx2 / (L2 * L2);                   // กิ่งสอง
  }

  // หา segment ที่ครอบ sta แล้วคืนระดับ
  function levelFromTable(segs, sta) {
    for (var i = 0; i < segs.length; i++) {
      var g = segs[i];
      var last = (i === segs.length - 1);
      if (sta >= g.staStart && (sta < g.staEnd || (last && sta <= g.staEnd))) {
        return levelAt(g, sta);
      }
    }
    return null;   // นอกช่วงข้อมูล
  }

  return { levelAt: levelAt, gradeAt: gradeAt, levelFromTable: levelFromTable };
})();

// ---- custom function สำหรับเรียกในเซลล์ (แทน VBA Ver) ----
function parseVertical_(table) {
  var segs = [];
  for (var i = 0; i < table.length; i++) {
    var r = table[i];
    if (r[1] === '' || r[1] === null || r[1] === undefined || isNaN(Number(r[1]))) continue;
    segs.push({
      staStart: Number(r[1]), staEnd: Number(r[2]), level: Number(r[3]),
      g1: Number(r[4]), g2: Number(r[5]), lvc: Number(r[6]) || 0,
      lvc2: (r[7] === undefined || r[7] === '') ? null : Number(r[7])
    });
  }
  return segs;
}

/** ระดับ ณ สถานี.  =VLEVEL(V_ROR4, sta) */
function VLEVEL(verTable, sta) {
  if (sta === '' || sta === null || sta === undefined) return '';
  var lv = Vertical.levelFromTable(parseVertical_(verTable), Number(sta));
  return lv === null ? '#STA_OUT' : lv;
}

/** เกรด(%) ณ สถานี.  =VGRADE(V_ROR4, sta) */
function VGRADE(verTable, sta) {
  if (sta === '' || sta === null || sta === undefined) return '';
  var segs = parseVertical_(verTable), x = Number(sta);
  for (var i = 0; i < segs.length; i++) {
    var g = segs[i], last = (i === segs.length - 1);
    if (x >= g.staStart && (x < g.staEnd || (last && x <= g.staEnd))) return Vertical.gradeAt(g, x);
  }
  return '#STA_OUT';
}

if (typeof module !== 'undefined' && module.exports) module.exports = Vertical;
