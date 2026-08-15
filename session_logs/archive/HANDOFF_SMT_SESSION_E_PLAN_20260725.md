# HANDOFF — แผนงาน Session E (cross-check table) และแผนต่อจากนี้ (2026-07-25)

**อ่านไฟล์นี้ก่อนเริ่ม session ใหม่ — สรุปทุกอย่างที่ตัดสินใจไปแล้ว + ขั้นตอนที่
เหลือให้ทำต่อ**

---

## 1. สถานะงานทั้งหมดจนถึงตอนนี้

| Session | เนื้อหา | สถานะ |
|---|---|---|
| A | สำรวจ Python core (element/cross-check logic ที่มีอยู่) | ✅ เสร็จ |
| B | พอร์ต `parse_pi_table()` → `GS_PiTableParser.gs` | ✅ เสร็จ |
| C | ต่อ pipeline เต็ม split→parse→build, verify end-to-end | ✅ เสร็จ |
| D | Export ตารางที่ 1 (element table) → `GS_ElementTable.gs` | ✅ เสร็จ |
| **E** | **Export ตารางที่ 2 (cross-check, 3 ตารางย่อย) — ออกแบบเสร็จ ยังไม่เขียนโค้ด** | ⬜ **จุดที่ทำต่อ** |
| F | หน้าเว็บจริง (`doGet()`+HTML) | ⬜ ยังไม่เริ่ม |

**ไฟล์ทั้งหมดที่มีอยู่แล้วใน repo** (`reference/gsheet/`): `GS_TableSplitter.gs`,
`GS_PiTableParser.gs`, `GS_AlignmentBuilder.gs` (v2.0, oracle ที่ถูกต้อง),
`GS_Alignment.gs`, `GS_ElementTable.gs` — ทั้งหมด push เข้า
`D:\MyClasp_SMT_DEMO\` แล้ว พร้อม `FPMath.js`/`WCB.js` ที่เพิ่มเข้าไปด้วยตอน
Session C

**Commit ล่าสุด**: `118234b` (Session D docs) เป็น HEAD ของ `origin/main`

**ข้อมูลทดสอบจริง**: Sheet `HOR-ORR-04` (ID
`1rEGH78P6vceamCIAUOVxKJSmAmK7aujnsY8iH3OcKsA`) — 36 แถว ข้อมูลถูกต้องครบ
(PI-10 แก้ไขแล้ว) ยืนยันตรงกับไฟล์ hardcopy `test_data/HOR_ORR_04N.csv` แล้ว
(ต่างแค่ 1-4mm ที่ STA บางจุด ไม่กระทบงาน — ตัดสินใจใช้ข้อมูลชีตจริงต่อไปเลย)

---

## 2. Session E — ออกแบบเสร็จสมบูรณ์แล้ว สรุปทั้งหมด

### 2.1 โครงสร้าง: แยกเป็น 3 ตาราง (ไม่ใช่ตารางเดียว)

**ตาราง 2a — เทียบจุดตามแบบ** (สำหรับ PC/PT/TS/SC/CS/ST ทุกจุดใน `drawing` array)

| Name | STA | ΔN | ΔE | Gap |
|---|---|---|---|---|

**ตาราง 2b — เทียบรัศมีที่ PI** (เฉพาะ PI ที่มีโค้งธรรมดา ไม่มี spiral)

| Name | รัศมีออกแบบ | รัศมีจาก T_in | รัศมีจาก T_out | ΔRadius (T_in) | ΔRadius (T_out) |
|---|---|---|---|---|---|

**ตาราง 2c — เทียบมุม deflection ที่ PI** (เฉพาะ PI ที่มีโค้งธรรมดา ไม่มี spiral)

| Name | Deflection ออกแบบ | Deflection ตามแบบจริง | ΔDeflection |
|---|---|---|---|

**เหตุผลที่แยก 3 ตาราง**: CK1024 ยืนยันแล้วว่าต้องการแบบนี้ (ถามแล้วเลือก "3
ตารางได้หรือไม่" แทนตัวเลือกเดิมที่เสนอไปเป็นตารางเดียว/สองตาราง)

น่าจะเขียนแต่ละตารางลง Sheet tab แยกกัน (เช่น "CrossCheck_Points",
"CrossCheck_Radius", "CrossCheck_Deflection") ตาม pattern เดียวกับ tab
"Elements" ใน Session D — **ยังไม่ได้ยืนยันชื่อ tab ที่แน่นอน ถามผู้ใช้ก่อนเริ่ม
เขียนโค้ดจริง**

### 2.2 ตาราง 2a — logic (มีของเดิมให้ mirror)

อ่านซอร์สจริงแล้วจาก `check.py::check_horizontal()` — **ไม่ได้จับคู่ตามชื่อจุด
กับ `control` ที่ `buildFromPI` สร้าง** แต่ทำแบบนี้:

```python
def check_horizontal(elements, controls, tol=0.05):
    results = []
    for control_point in controls:  # controls = "drawing" array ของเรา
        name = control_point['name']
        sta_draw = control_point['sta']
        n_draw = control_point['n']
        e_draw = control_point['e']
        sta_eff = _snap_to_alignment_ends(sta_draw, elements)  # snap ถ้าใกล้ปลายแนวใน 0.01m
        calc = calculate_station_to_coordinate(elements, sta_eff, 0.0)  # offset=0 = centerline
        delta_n = calc.n - n_draw
        delta_e = calc.e - e_draw
        gap_metres = hypot(delta_n, delta_e)
        results.append({name, sta_draw, delta_n, delta_e, gap_metres, is_ok: gap<=tol})
    return results
```

`_snap_to_alignment_ends`: ถ้า sta อยู่นอกช่วงแนว (ก่อน element แรกหรือหลัง
element สุดท้าย) แต่ห่างไม่เกิน 0.01m ให้ปัดเข้าขอบแนว (กันพลาดกรณี EP ตามแบบ
ไม่ตรงเป๊ะกับ EP ที่คำนวณ เช่นที่เจอ EP ต่างกัน 0.0002m มาก่อนหน้านี้)

**ฝั่ง GAS**: `GS_Alignment.stationToCoord(elements, sta, offset)` ทำหน้าที่
เดียวกับ `calculate_station_to_coordinate` อยู่แล้ว (verify ไปแล้วใน Session C
ว่า geometry engine ถูกต้อง) — งานที่เหลือแค่ port `_snap_to_alignment_ends`
(ง่าย ไม่ซับซ้อน) + wrapper วนลูป `drawing` array เรียก `stationToCoord` แล้ว
คำนวณ delta — **นี่คืองาน mirror ตรงไปตรงมา เหมือน Session D**

Verify: รัน Python `check_horizontal()` จริงกับ `drawing` ของ `HOR_ORR_04.csv`
เทียบกับผลจาก GAS ผ่าน Node เหมือนที่ทำมาตลอด (diff=0)

### 2.3 ตาราง 2b/2c — logic ใหม่ทั้งหมด (ไม่มีของเดิมให้ mirror)

สำหรับแต่ละ PI ที่**ไม่มี spiral** (ไม่มี `Ls`/`LsIn`/`LsOut` และไม่ใช่
compound):

1. หาแถว **PC ก่อนหน้า** และ **PT ถัดไป** ใน `drawing` array ที่ล้อมรอบ PI นี้
   (ตามลำดับที่ปรากฏในตารางดิบต้นฉบับ — ต้องคง**ลำดับเดิม**ของแถวไว้ตั้งแต่ตอน
   split เพื่อให้จับคู่ PC/PT กับ PI ที่ถูกต้องได้)
2. `T_in` = ระยะจาก PI ถึง PC จริง (`distance2D`)
3. `T_out` = ระยะจาก PI ถึง PT จริง (`distance2D`)
4. **มุม deflection ตามแบบจริง** = มุมระหว่างเวกเตอร์ (PI→PC จริง) กับ
   (PI→PT จริง) — คำนวณจากพิกัดจริงล้วนๆ ไม่พึ่ง azimuth chain ที่ใช้สร้างแนว
   (ใช้ `atan2`/`angleDiff` ของ `FPMath`/`WCB` ที่มีอยู่แล้ว)
5. **รัศมีจาก T_in** = `T_in / tan(Δจริง / 2)`
6. **รัศมีจาก T_out** = `T_out / tan(Δจริง / 2)`
7. **มุม deflection ออกแบบ** = คำนวณเองจากพิกัด PI ในตาราง PI ต้นฉบับ (BP/PI
   ก่อนหน้า → PI นี้ → PI/EP ถัดไป) ด้วยสูตรเดียวกับที่ `buildFromPI` ใช้ภายใน
   (แต่**คำนวณแยกต่างหาก ไม่ดึงจาก `buildFromPI` ตรงๆ** เพราะค่านี้เป็นตัวแปร
   ภายในที่ไม่ได้ถูก return ออกมา — เขียนฟังก์ชันเล็กๆ คำนวณซ้ำเอาเอง ไม่แก้
   `buildFromPI`/`GS_AlignmentBuilder.gs` เลย)
8. **ΔRadius (T_in)** = รัศมีจาก T_in − รัศมีออกแบบ (จากตาราง PI, ค่า `R`)
9. **ΔRadius (T_out)** = รัศมีจาก T_out − รัศมีออกแบบ
10. **ΔDeflection** = deflection ตามแบบจริง − deflection ออกแบบ

**ยังไม่ตัดสินใจ / ควรถามก่อนเขียนโค้ด**:
- หน่วยของ ΔDeflection (องศา หรือ radian?) — แนะนำองศา (อ่านง่ายกว่าสำหรับ
  งานสำรวจ)
- PI ที่เป็น angle point (ไม่มีโค้งเลย ไม่มี R) — ไม่มีรัศมี/deflection ให้เทียบ
  เช่นกัน (ไม่ใช่แค่ PI มี spiral) ต้อง skip ด้วยเหมือนกัน — ควรยืนยันตรงนี้ให้
  ชัดตอนเริ่ม Session E

**Verify**: ไม่มี Python function ให้ diff=0 ตรงๆ (logic ใหม่ทั้งหมด) —
แนะนำ:
1. เขียน logic นี้เป็น Python เวอร์ชันสั้นๆ ก่อน (prototype ในเครื่อง ไม่ต้องเข้า
   repo) ยืนยันด้วยมือ 1-2 จุดจริง (เช่น คำนวณ PI-1 ด้วยเครื่องคิดเลข/กระดาษ
   เทียบกับ prototype)
2. เขียน GAS version คู่ขนาน รัน Node เทียบกับ prototype Python (diff=0)
3. ค่อยพอร์ตเข้า repo จริง

### 2.4 การจับคู่ PI กับ PC/PT ข้างเคียง — จุดที่ต้องระวังตอนเขียนโค้ด

`GS_TableSplitter.splitMixedAlignmentTable()` ปัจจุบันแยกแค่ `vertexRows`
(PI ทั้งหมด) กับ `drawing` (PC/PT ทั้งหมด) เป็น 2 array แยกกัน **ไม่ได้เก็บ
ลำดับสลับเดิมของทั้งตารางไว้** (เช่น "BP, PI-1, PT, PC, PI-2, ..." เดิมหายไป
เมื่อแยกเป็น 2 กอง) — ต้องหาวิธีคืนลำดับเดิมกลับมาก่อนถึงจะจับคู่ PI กับ PC/PT
ข้างเคียงถูกต้อง

**ทางเลือก**:
(ก) แก้/เขียนฟังก์ชันใหม่ที่เดินตาม `rows` ต้นฉบับ (ก่อน split) โดยตรง แล้วจับคู่
    ไปในตัว (ไม่ต้องพึ่ง `vertexRows`/`drawing` ที่ split ไปแล้ว)
(ข) ให้ `GS_TableSplitter` (หรือฟังก์ชันใหม่) คืนค่า index ต้นฉบับของแต่ละแถว
    ติดมาด้วย เพื่อจับคู่ย้อนกลับได้

แนะนำ (ก) — เขียนฟังก์ชันใหม่เดินตาม `rows` ดิบเองตรงๆ สำหรับงานจับคู่นี้
โดยเฉพาะ ไม่ต้องแก้ `GS_TableSplitter.gs` เดิมที่ verify ไปแล้ว

---

## 3. ขั้นตอนที่แนะนำสำหรับ Session E (ทำต่อรอบหน้า)

1. **ยืนยันคำถามที่ค้าง** (หัวข้อ 2.3): หน่วย deflection, การจัดการ PI
   angle-point, ชื่อ Sheet tab ทั้ง 3
2. **เขียน prototype ตาราง 2b/2c เป็น Python ก่อน** ยืนยันด้วยมือ 1-2 จุด
3. **เขียน GS_CrossCheck.gs** (ชื่อไฟล์ตัวอย่าง) ครอบคลุมทั้ง 3 ตาราง:
   - ฟังก์ชัน mirror `check_horizontal()` (ตาราง 2a) — verify diff=0 กับ Python
     จริง (`check.py::check_horizontal()`)
   - ฟังก์ชันจับคู่ PI↔PC/PT จากตารางดิบ (หัวข้อ 2.4)
   - ฟังก์ชันคำนวณรัศมี/deflection ตามแบบ (ตาราง 2b/2c) — verify กับ prototype
     Python (ข้อ 2)
4. **เขียนฟังก์ชัน export ทั้ง 3 ตารางลง Sheet tabs** (ตาม pattern
   `exportElementsToSheet` ของ Session D — เช็ค tab มีอยู่แล้วหรือยัง, clear
   หรือ insertSheet, `setValues()` ครั้งเดียว)
5. **เขียนฟังก์ชันทดสอบรวม pipeline เต็ม** (split→parse→build→export ตาราง 1
   +2a+2b+2c) รันกับ Sheet `HOR-ORR-04` จริง
6. Commit (แยก feat + docs/session-log ตาม pattern เดิม), push
7. บันทึกเป็น known limitation ในเอกสาร: PI ที่มี spiral/angle-point ไม่มี
   radius/deflection delta ให้ดู (ตาราง 2b/2c จะไม่มีแถวสำหรับ PI เหล่านั้น)

**หลัง Session E เสร็จ**: CK1024 อยากให้เอาไปใช้งานจริงก่อน รอ feedback จากคนอื่น
แล้วค่อยกลับมาปรับปรุงทีหลัง (ยังไม่ต้องรีบไป Session F ทันที — รอดูว่า
Session E ใช้งานจริงแล้วเป็นยังไงก่อน)

---

## 4. ข้อความสำหรับเริ่ม session ใหม่

```
นี่คือแผนงาน Session E ฉบับละเอียด (แนบไฟล์
HANDOFF_SMT_SESSION_E_PLAN_20260725.md) — ออกแบบเสร็จสมบูรณ์แล้วทั้ง 3 ตาราง
(2a เทียบจุดตามแบบ, 2b เทียบรัศมี, 2c เทียบ deflection) เหลือแค่เขียนโค้ดจริง
เริ่มจากข้อ 3.1 (ยืนยันคำถามค้างเรื่องหน่วย deflection/PI angle-point/ชื่อ tab)
ก่อนเขียนโค้ดครับ
```
