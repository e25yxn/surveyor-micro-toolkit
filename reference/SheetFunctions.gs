/**
 * ============================================================================
 *  SheetFunctions.gs — Custom Functions เรียกใช้จากเซลล์ใน Google Sheet
 * ----------------------------------------------------------------------------
 *  เหมือน VBA Public Function ที่เรียกใน Excel ได้ ต่างกันแค่รับ "ช่วงตาราง"
 *  (Named Range) เข้ามาเป็น array  —  คือ Define Name "ORR4" ของคุณนั่นเอง
 *
 *  รูปแบบตาราง element (Named Range) ต้องมี 7 คอลัมน์ เรียงตามนี้:
 *    [StaStart] [StaEnd] [N] [E] [Azimuth(องศา)] [Radius] [Type]
 *    - Radius: 0 = tangent, บวก = เลี้ยวขวา, ลบ = เลี้ยวซ้าย
 *    - Type:   T / C  (SPIN, SPOUT รอ Phase 1b)
 *
 *  (ต้องมี FPMath.gs, WCB.gs, Alignment.gs ในโปรเจกต์)
 * ============================================================================
 */

/**
 * แปลงช่วงตาราง (2D array จากเซลล์) -> ลิสต์ element
 * (มี _ ต่อท้าย = ฟังก์ชันภายใน เรียกจากเซลล์ไม่ได้)
 */
function parseTable_(table) {
  var els = [];
  for (var i = 0; i < table.length; i++) {
    var r = table[i];
    var v = r[0];
    if (v === '' || v === null || v === undefined) continue;  // ข้ามแถวว่าง
    if (isNaN(Number(v))) continue;                           // ข้ามแถวหัวตาราง
    els.push(Alignment.makeElement(
      String(r[6]).trim(),   // Type
      Number(r[0]),          // StaStart
      Number(r[1]),          // StaEnd
      Number(r[2]),          // N
      Number(r[3]),          // E
      Number(r[4]),          // Azimuth (องศา)
      Number(r[5]),          // Radius
      undefined,             // rOut (โหมดคอลัมน์เดียว)
      r[7]                   // Transition (ว่าง = CLOTHOID)
    ));
  }
  return els;
}

/**
 * Northing จาก station + offset
 * @param {Array} table ช่วงตาราง element (Named Range เช่น ORR4)
 * @param {number} sta ค่า station
 * @param {number} offset ระยะเยื้อง (+ขวา, -ซ้าย); เว้นว่าง = 0
 * @return {number} ค่า Northing
 * @customfunction
 */
function FWD_N(table, sta, offset) {
  try { return Alignment.stationToCoord(parseTable_(table), sta, offset || 0).n; }
  catch (err) { return '#' + err.message; }
}

/**
 * Easting จาก station + offset
 * @param {Array} table ช่วงตาราง element (Named Range)
 * @param {number} sta ค่า station
 * @param {number} offset ระยะเยื้อง (+ขวา, -ซ้าย); เว้นว่าง = 0
 * @return {number} ค่า Easting
 * @customfunction
 */
function FWD_E(table, sta, offset) {
  try { return Alignment.stationToCoord(parseTable_(table), sta, offset || 0).e; }
  catch (err) { return '#' + err.message; }
}

/**
 * station จากพิกัด N,E (Inverse)
 * @param {Array} table ช่วงตาราง element (Named Range)
 * @param {number} n ค่า Northing
 * @param {number} e ค่า Easting
 * @return {number} ค่า station
 * @customfunction
 */
function INV_STA(table, n, e) {
  try { return Alignment.coordToStation(parseTable_(table), n, e).sta; }
  catch (err) { return '#' + err.message; }
}

/**
 * offset จากพิกัด N,E (Inverse) — ใช้ตรวจ pile deviation
 * @param {Array} table ช่วงตาราง element (Named Range)
 * @param {number} n ค่า Northing
 * @param {number} e ค่า Easting
 * @return {number} ระยะเยื้องจาก center line (+ขวา, -ซ้าย)
 * @customfunction
 */
function INV_OFFSET(table, n, e) {
  try { return Alignment.coordToStation(parseTable_(table), n, e).offset; }
  catch (err) { return '#' + err.message; }
}

/* ----------------------------------------------------------------------------
 *  WCB (Azimuth) ของแนว ณ ตำแหน่ง — ใช้ค่า az (tangent) จาก pointOnElement
 *  ที่ engine คำนวณอยู่แล้ว (FWD_N/INV_STA ทิ้งค่านี้ไป)  => ไม่ต้องแก้ engine
 *  คืนเป็น "องศา decimal" (0..360) ให้ตรงกับคอลัมน์ Azimuth ในตาราง
 * -------------------------------------------------------------------------- */

/** az (radian) ของแนว ณ station — ฟังก์ชันภายใน */
function azimuthAtSta_(els, sta) {
  var i = Alignment.findElementIndex(els, sta);
  if (i < 0) throw new Error('station ' + sta + ' อยู่นอกแนวเส้นทาง');
  return Alignment.pointOnElement(els[i], sta - els[i].staStart).az;
}

/**
 * WCB (Azimuth) ของแนว ณ station  — คู่กับ FWD_N
 *  offset ไม่มีผลต่อทิศ (เส้นขนานมีทิศเดียวกัน) รับไว้ให้รูปแบบตรงกับ FWD_N
 * @param {Array} table ช่วงตาราง element (Named Range เช่น ORR4)
 * @param {number} sta ค่า station
 * @param {number} offset (ไม่มีผล) เว้นว่างได้
 * @return {number} azimuth องศา decimal (0..360)
 * @customfunction
 */
function FWD_WCB(table, sta, offset) {
  try { return FPMath.radToDeg(azimuthAtSta_(parseTable_(table), Number(sta))); }
  catch (err) { return '#' + err.message; }
}

/**
 * WCB (Azimuth) ของแนว ณ จุด N,E (โปรเจกต์ลงแนวก่อน)  — คู่กับ INV_STA
 * @param {Array} table ช่วงตาราง element (Named Range)
 * @param {number} n ค่า Northing
 * @param {number} e ค่า Easting
 * @return {number} azimuth องศา decimal (0..360)
 * @customfunction
 */
function INV_WCB(table, n, e) {
  try {
    var els = parseTable_(table);
    var r = Alignment.coordToStation(els, Number(n), Number(e));
    return FPMath.radToDeg(azimuthAtSta_(els, r.sta));
  } catch (err) { return '#' + err.message; }
}

/**
 * Forward รวม -> คืน [N, E] (กระจายลง 2 เซลล์)
 * @param {Array} table ช่วงตาราง element (Named Range)
 * @param {number} sta ค่า station
 * @param {number} offset ระยะเยื้อง; เว้นว่าง = 0
 * @return {Array} [N, E]
 * @customfunction
 */
function FWD(table, sta, offset) {
  try {
    var p = Alignment.stationToCoord(parseTable_(table), sta, offset || 0);
    return [[p.n, p.e]];
  } catch (err) { return '#' + err.message; }
}

/**
 * Inverse รวม -> คืน [station, offset] (กระจายลง 2 เซลล์)
 * @param {Array} table ช่วงตาราง element (Named Range)
 * @param {number} n ค่า Northing
 * @param {number} e ค่า Easting
 * @return {Array} [station, offset]
 * @customfunction
 */
function INV(table, n, e) {
  try {
    var r = Alignment.coordToStation(parseTable_(table), n, e);
    return [[r.sta, r.offset]];
  } catch (err) { return '#' + err.message; }
}

/* ============================================================================
 *  รองรับหลาย alignment ในตารางเดียว (Master Table)
 * ----------------------------------------------------------------------------
 *  รูปแบบ Master Table 8 คอลัมน์ (เพิ่ม "ชื่อแนว" เป็นคอลัมน์แรก):
 *    [Alignment] [StaStart] [StaEnd] [N] [E] [Azimuth] [Radius] [Type]
 *  วางทุกแนวในชีตเดียว เพิ่มแถวได้เรื่อยๆ แล้วเลือกแนวด้วยชื่อ (เหมือน database)
 *
 *  SETOUT_* = วางตำแหน่ง (forward),  CHECK_* = ตรวจสอบ (inverse)
 * ========================================================================== */

/** แปลง Master Table -> ลิสต์ element เฉพาะแนวที่ชื่อตรงกับ name (ภายใน) */
function parseAlignment_(table, name) {
  var target = String(name).trim();
  var els = [];
  for (var i = 0; i < table.length; i++) {
    var r = table[i];
    if (String(r[0]).trim() !== target) continue;       // กรองเฉพาะแนวที่ต้องการ
    if (r[1] === '' || isNaN(Number(r[1]))) continue;    // ข้ามแถวหัว/ว่าง
    els.push(Alignment.makeElement(
      String(r[7]).trim(),   // Type
      Number(r[1]),          // StaStart
      Number(r[2]),          // StaEnd
      Number(r[3]),          // N
      Number(r[4]),          // E
      Number(r[5]),          // Azimuth (องศา)
      Number(r[6]),          // Radius
      undefined,             // rOut (โหมดคอลัมน์เดียว)
      r[8]                   // Transition (ว่าง = CLOTHOID)
    ));
  }
  if (els.length === 0) throw new Error('ไม่พบแนว "' + target + '"');
  return els;
}

/**
 * Northing — วางตำแหน่งบนแนวที่ระบุชื่อ
 * @param {Array} table Master Table (Named Range)
 * @param {string} align ชื่อแนว เช่น "ORR4"
 * @param {number} sta ค่า station
 * @param {number} offset ระยะเยื้อง (+ขวา,-ซ้าย); เว้นว่าง = 0
 * @return {number} Northing
 * @customfunction
 */
function SETOUT_N(table, align, sta, offset) {
  try { return Alignment.stationToCoord(parseAlignment_(table, align), sta, offset || 0).n; }
  catch (err) { return '#' + err.message; }
}

/**
 * Easting — วางตำแหน่งบนแนวที่ระบุชื่อ
 * @param {Array} table Master Table (Named Range)
 * @param {string} align ชื่อแนว
 * @param {number} sta ค่า station
 * @param {number} offset ระยะเยื้อง; เว้นว่าง = 0
 * @return {number} Easting
 * @customfunction
 */
function SETOUT_E(table, align, sta, offset) {
  try { return Alignment.stationToCoord(parseAlignment_(table, align), sta, offset || 0).e; }
  catch (err) { return '#' + err.message; }
}

/**
 * station ของจุด N,E บนแนวที่ระบุชื่อ (ตรวจสอบ)
 * @param {Array} table Master Table (Named Range)
 * @param {string} align ชื่อแนว
 * @param {number} n Northing
 * @param {number} e Easting
 * @return {number} station
 * @customfunction
 */
function CHECK_STA(table, align, n, e) {
  try { return Alignment.coordToStation(parseAlignment_(table, align), n, e).sta; }
  catch (err) { return '#' + err.message; }
}

/**
 * offset ของจุด N,E บนแนวที่ระบุชื่อ (ตรวจ pile deviation)
 * @param {Array} table Master Table (Named Range)
 * @param {string} align ชื่อแนว
 * @param {number} n Northing
 * @param {number} e Easting
 * @return {number} ระยะเยื้องจาก center line (+ขวา,-ซ้าย)
 * @customfunction
 */
function CHECK_OFFSET(table, align, n, e) {
  try { return Alignment.coordToStation(parseAlignment_(table, align), n, e).offset; }
  catch (err) { return '#' + err.message; }
}

/**
 * WCB (Azimuth) ของแนวที่ระบุชื่อ ณ station — คู่กับ SETOUT_N (Master Table)
 * @param {Array} table Master Table (Named Range)
 * @param {string} align ชื่อแนว
 * @param {number} sta ค่า station
 * @param {number} offset (ไม่มีผล) เว้นว่างได้
 * @return {number} azimuth องศา decimal (0..360)
 * @customfunction
 */
function SETOUT_WCB(table, align, sta, offset) {
  try { return FPMath.radToDeg(azimuthAtSta_(parseAlignment_(table, align), Number(sta))); }
  catch (err) { return '#' + err.message; }
}

/**
 * WCB (Azimuth) ของแนวที่ระบุชื่อ ณ จุด N,E — คู่กับ CHECK_STA (Master Table)
 * @param {Array} table Master Table (Named Range)
 * @param {string} align ชื่อแนว
 * @param {number} n ค่า Northing
 * @param {number} e ค่า Easting
 * @return {number} azimuth องศา decimal (0..360)
 * @customfunction
 */
function CHECK_WCB(table, align, n, e) {
  try {
    var els = parseAlignment_(table, align);
    var r = Alignment.coordToStation(els, Number(n), Number(e));
    return FPMath.radToDeg(azimuthAtSta_(els, r.sta));
  } catch (err) { return '#' + err.message; }
}

/**
 * WCB (Azimuth, องศา) บนแนวที่ระบุชื่อ ณ station — คู่กับ SETOUT_N
 * @param {Array} table Master Table (Named Range)
 * @param {string} align ชื่อแนว
 * @param {number} sta ค่า station
 * @param {number} offset (ไม่มีผลต่อทิศ) เว้นว่างได้
 * @return {number} azimuth องศา decimal (0..360)
 * @customfunction
 */
function SETOUT_WCB(table, align, sta, offset) {
  try { return FPMath.radToDeg(azimuthAtSta_(parseAlignment_(table, align), Number(sta))); }
  catch (err) { return '#' + err.message; }
}

/**
 * WCB (Azimuth, องศา) บนแนวที่ระบุชื่อ ณ จุด N,E — คู่กับ CHECK_STA
 * @param {Array} table Master Table (Named Range)
 * @param {string} align ชื่อแนว
 * @param {number} n Northing
 * @param {number} e Easting
 * @return {number} azimuth องศา decimal (0..360)
 * @customfunction
 */
function CHECK_WCB(table, align, n, e) {
  try {
    var els = parseAlignment_(table, align);
    var r = Alignment.coordToStation(els, Number(n), Number(e));
    return FPMath.radToDeg(azimuthAtSta_(els, r.sta));
  } catch (err) { return '#' + err.message; }
}

/**
 * วางตำแหน่งรวม -> คืน [N, E] (กระจาย 2 เซลล์)
 * @param {Array} table Master Table (Named Range)
 * @param {string} align ชื่อแนว
 * @param {number} sta ค่า station
 * @param {number} offset ระยะเยื้อง; เว้นว่าง = 0
 * @return {Array} [N, E]
 * @customfunction
 */
function SETOUT(table, align, sta, offset) {
  try {
    var p = Alignment.stationToCoord(parseAlignment_(table, align), sta, offset || 0);
    return [[p.n, p.e]];
  } catch (err) { return '#' + err.message; }
}

/**
 * ตรวจสอบรวม -> คืน [station, offset] (กระจาย 2 เซลล์)
 * @param {Array} table Master Table (Named Range)
 * @param {string} align ชื่อแนว
 * @param {number} n Northing
 * @param {number} e Easting
 * @return {Array} [station, offset]
 * @customfunction
 */
function CHECK(table, align, n, e) {
  try {
    var r = Alignment.coordToStation(parseAlignment_(table, align), n, e);
    return [[r.sta, r.offset]];
  } catch (err) { return '#' + err.message; }
}
