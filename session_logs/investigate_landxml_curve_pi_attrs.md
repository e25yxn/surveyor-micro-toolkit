Investigation: เพิ่ม attribute + <PI> sub-tag ให้ <Curve>/<Spiral> ใน LandXML export
(ตรวจสอบสูตรก่อนวางแผนแก้ ยังไม่แก้โค้ดใดๆ ในรอบนี้)
วันที่ 2026-07-06
ประเภทงาน ตรวจสอบ/รายงาน ยังไม่มีการแก้โค้ด ยังไม่เขียนแผน

## หนึ่ง — export_alignment_landxml เต็มฟังก์ชัน (src/smt/landxml.py บรรทัด 131-243)

ฟังก์ชันอยู่ที่ src/smt/landxml.py ทั้งไฟล์มี 244 บรรทัด structure หลักคือ loop
`for i, el in enumerate(elements):` (บรรทัด 174-239) แยก 4 กรณีตาม el.type: 'T' (Line),
'C' (Curve), 'SPIN'/'SPOUT' (Spiral)

จุดที่เกี่ยวข้องกับงานนี้คือ branch `elif el.type == 'C':` (บรรทัด 184-197):

```python
elif el.type == 'C':
    k = el.k_in
    R = abs(1.0 / k)
    cn, ce = _curve_center(el.n, el.e, el.azimuth, k)
    exit_az = _exit_azimuth(i, elements)
    tag = ET.SubElement(coord_geom, f'{{{_NS}}}Curve',
                        rot=_rotation(k),
                        radius=f'{R:.6f}',
                        length=f'{length:.6f}',
                        dirStart=f'{_to_civil_dir(el.azimuth):.6f}',
                        dirEnd=f'{_to_civil_dir(exit_az):.6f}')
    _sub(tag, 'Start',  _coord(el.n, el.e))
    _sub(tag, 'Center', _coord(cn, ce))
    _sub(tag, 'End',    _coord(end_n, end_e))
```

ตัวแปรที่มีอยู่แล้วในสโคปนี้ตอนนี้: `k` (=el.k_in, signed curvature), `R` (=abs(1/k)),
`cn, ce` (จุดศูนย์กลาง), `exit_az` (azimuth ขาออก จาก `_exit_azimuth(i, elements)`), `length`
(= el.sta_end - el.sta_start คำนวณบรรทัด 176 ก่อนเข้า if/elif ทุกกรณี), `el.n, el.e`
(จุดเริ่ม Curve), `end_n, end_e` (จุดจบ Curve จาก `_end_ne(i, elements)` บรรทัด 175)

ยังไม่มีตัวแปร `delta`/Δ ในสโคปนี้เลย — ต้องคำนวณเพิ่มด้วย `_theta_rad(el.azimuth, exit_az)`
ซึ่งเป็นฟังก์ชันเดียวกับที่ branch SPIN/SPOUT เรียกอยู่แล้ว (บรรทัด 203, 224) มีอยู่แล้วในไฟล์
ไม่ต้องเขียนใหม่ — ใช้ได้ตรงๆ กับ Curve เช่นกัน เพราะ `_theta_rad` รับแค่ entry/exit azimuth
ไม่ผูกกับชนิด element

branch spiral (SPIN บรรทัด 199-218, SPOUT บรรทัด 220-239) มีตัวแปร `theta_rad` และ
`tan_long` (จาก `_spiral_geometry`) อยู่แล้วในสโคปนี้ — พอสำหรับสูตร PI ของ Spiral ที่โจทย์
ต้องการโดยไม่ต้องคำนวณอะไรเพิ่ม

## สอง+สาม — ทดสอบสูตรด้วยการรันจริง 2 เส้นทาง (hand-built vertices และ CSV → CLI เต็ม)

ทดสอบ 2 เส้นทางแยกกัน:
1. เรียก `build_alignment_from_pi` ตรงๆ ด้วย vertex dict ที่สร้างเอง (ไม่ผ่าน CSV parser)
2. เขียน PI table เป็นไฟล์ CSV จริงที่ scratchpad
   (`pi_table_ground_truth.csv`, format `POINT,STA,NORTHING,EASTING,RADIUS,LsIn,LsOut,Transition`
   ตามที่โจทย์ให้) แล้วรัน `smt export-landxml` จริงผ่าน CLI (เรียก `_read_pi_table` →
   `parse_pi_table` → `build_alignment_from_pi` → `export_alignment_landxml` ครบ pipeline)

PI table ที่ใช้ทดสอบ:
```
BP,   n=1543078.851,  e=682175.2221
PI1,  n=1543275.044,  e=682214.0623,  R=100,   Ls=35, trans=CLOTHOID
PI2,  n=1543368.699,  e=682416.2292,  R=-105,  Ls=40, trans=CLOTHOID
EP,   n=1543573.554,  e=682458.492
```

**ทั้งสองเส้นทางให้ตัวเลขตรงกันทุกหลัก** (เป็นโค้ดเดียวกัน — `_read_pi_table` แค่แปลง CSV
เป็น vertex dict แบบเดียวกับที่ hand-built ไว้ก่อนหน้า ไม่มีจุดใดต่างกันระหว่างทาง) ยืนยันแค่ว่า
pipeline เต็มไม่มีจุดรั่วหรือจุดปัดเศษระหว่างทาง **ไม่ได้ยืนยันว่าตรงกับ Civil 3D**

ผลลัพธ์ elements ที่ build ได้ (9 element: T, SPIN, C, SPOUT, T, SPIN, C, SPOUT, T) —
ไม่มี issue ใดๆ (`result.issues == []`)

Curve แรก (element index 2, R=100.0):
- Δ ของ Curve เอง (ไม่ใช่ Δ รวมของทั้ง PI) คำนวณจาก
  `_theta_rad(el.azimuth, exit_az)` ของ element index 2 นั้นเอง = 33.892254 องศา
  (Δ รวมของ PI1 ทั้งก้อน รวม spiral ทั้งสองข้างด้วย จริงๆ คือ 53.94 องศา — คนละค่ากัน
  ยืนยันว่าต้องใช้ Δ เฉพาะของ element 'C' นั้นๆ ไม่ใช่ Δ ของ PI ทั้งหมด)
- tangent  = R·tan(Δ/2)          = 30.470282988   Civil3D 30.470311074669
             diff = -0.000028087 ม. (0.028 มม.)
- chord    = 2R·sin(Δ/2)         = 58.294480193   Civil3D 58.294529362525
             diff = -0.000049169 ม. (0.049 มม.)
- external = R·(1/cos(Δ/2) − 1)  = 4.539170388    Civil3D 4.539178574294
             diff = -0.000008186 ม. (0.008 มม.)
- midOrd   = R·(1 − cos(Δ/2))    = 4.342076153    Civil3D 4.342083643854
             diff = -0.000007491 ม. (0.0075 มม.)
- PI point = Start + tangent·(cos az, sin az)
           = 1543269.952528835, 682220.539170882
    Civil3D = 1543269.952250064351, 682220.539152466343
    diff_n = 0.000278770 ม. (0.28 มม.)   diff_e = 0.000018416 ม. (0.018 มม.)

Spiral แรก (SPIN, element index 1, R=100.0, length=35.0):
- tanLong = 23.370873972 (ตรงกับที่ `_spiral_geometry` คำนวณอยู่แล้วในปัจจุบัน ตรงกับที่
  โจทย์ระบุ 23.370873963336 — ต่างกันแค่ 1e-8 ระดับ float noise ปกติ)
- PI point = Start + tanLong·(cos az, sin az)
           = 1543230.642020991, 682205.272069232
    Civil3D = 1543230.641722853528, 682205.272023039055
    diff_n = 0.000298138 ม. (0.30 มม.)   diff_e = 0.000046193 ม. (0.046 มม.)

**สรุปตรงๆ: ตัวเลขที่คำนวณได้ไม่ตรงกับ Civil 3D เป๊ะ** ต่างกันอยู่ในช่วง
0.000008–0.0003 เมตร (0.008–0.30 มม.) ทุกค่า สาเหตุที่เป็นไปได้ (ยังไม่ได้พิสูจน์ยืนยัน
เป็นสมมติฐานเท่านั้น):
1. Civil 3D น่าจะคำนวณ/แก้ alignment geometry ใหม่เองหลัง import LandXML จาก
   Start/Center/radius/length ที่เราส่งให้ ไม่ได้ preserve ค่าดิบที่เราคำนวณไว้ ค่า
   tangent/chord/PI point ที่ Civil 3D รายงานจึงอาจเป็นผลจากการคำนวณใหม่ภายในของ
   Civil 3D เอง ไม่ใช่การสะท้อนค่าเดิมแบบตรงเป๊ะ
2. ความคลาดเคลื่อนสะสมจาก floating point ตลอดสายการคำนวณหลาย PI ต่อเนื่องกัน (แก้สมการ
   2×2 หา tangent length ที่แต่ละ PI ต่อเนื่องกัน ผ่าน trig หลายชั้น) รวมกับการปัด
   coordinate ในไฟล์ XML ที่ 6 ตำแหน่งทศนิยม (`_coord`) — ข้อนี้เพียงอย่างเดียวคาดว่า
   เล็กกว่าขนาดที่สังเกตได้ (ระดับไมครอน ไม่ใช่ระดับ 0.1–0.3 มม.)
ยังไม่มีหลักฐานเพียงพอจะฟันธงว่าอันไหนเป็นสาเหตุหลัก ต้องสืบเพิ่มถ้าต้องการ tolerance
ที่แคบกว่านี้

ขนาดผลต่าง (สูงสุด 0.30 มม.) เล็กกว่า 1 มม. ที่โปรเจกต์นี้เคยใช้เป็นบรรทัดฐานยืนยัน
ground truth มาก่อน (compound curve ใน CLAUDE.md "ยืนยันตรงกับ SMT output ต่ำกว่า
1 มิลลิเมตร") แต่เป็นคนละระดับความมั่นใจกับคำว่า "ยืนยันแล้ว"/"ตรงกันแล้ว" — ควรเขียนแผน
ต่อโดยตั้ง tolerance การ assert ใน test ใหม่ที่ระดับ ~0.5 มม. (ไม่ใช่ 1e-6 แบบ test เดิม
ในไฟล์ที่ใช้ synthetic input แม่นยำ) และระบุใน docstring/commit message ว่าเป็นการ
ประมาณใกล้เคียง Civil 3D ไม่ใช่ closed-form ที่ตรงเป๊ะ

## สี่ — สคริปต์ยืนยันที่ใช้จริง (บันทึกไว้เป็น scratch ไม่ใส่ tests/ หรือ test_data/)

- เส้นทางที่ 1 (hand-built vertices): `/tmp/verify_pi.py`
- เส้นทางที่ 2 (CSV → CLI เต็ม): CSV ที่
  `C:/Users/CK1024/AppData/Local/Temp/claude/D--My-Second-Project-SurveyorMicroToolkit/
  d1201944-37db-4b5e-b9f8-6d43f48ed61a/scratchpad/pi_table_ground_truth.csv`
  รันจริงด้วย `smt export-landxml <csv> --out /tmp/pi_ground_truth.xml` แล้ววิเคราะห์ผลด้วย
  `/tmp/verify_pi_pipeline.py` (เรียก `_read_pi_table` ตัวเดียวกับที่ CLI เรียกจริง)
ทั้งสองไฟล์เป็น scratch ชั่วคราวใน temp directory ไม่ใช่ไฟล์ถาวรของโปรเจกต์

## ห้า — grep tests/test_landxml.py หา chord, delta, tangent, external, midOrd, PI

grep คำว่า `chord|delta|tangent|external|midOrd|PI` ทั้งไฟล์ (370 บรรทัด) เจอ 2 จุด:
- บรรทัด 36 comment `# PI vertex helpers` (ชื่อ comment ของ helper function สร้าง vertex
  dict สำหรับ test ไม่เกี่ยวกับ XML attribute)
- บรรทัด 166 comment อธิบาย `test_curve_dir_start` ("BP→PI direction is East...")

**สรุป: ไม่มี test ใดใน tests/test_landxml.py ที่ตรวจสอบ attribute chord, tangent,
external, midOrd, delta หรือ PI sub-tag เลยแม้แต่ตัวเดียว** — งานนี้จึงไม่กระทบ test เดิม
เลยแม้แต่ตัวเดียว (ไม่มี test ไหน assert ว่า Curve/Spiral element ต้องมี attribute ครบตามจำนวน
หรือห้ามมี attribute เกิน จึงไม่มีความเสี่ยงที่จะทำให้ test เดิมพังจากการเพิ่ม attribute ใหม่)
ต้องเพิ่ม regression test ใหม่ทั้งหมดในแผนถัดไป อย่างน้อยครอบคลุม:
- tangent/chord/external/midOrd ของ Curve (ค่าคำนวณจาก R และ Δ เฉพาะของ Curve element
  tolerance ~0.5 มม. ไม่ใช่ 1e-6 เทียบ ground truth Civil 3D จริง)
- crvType="arc" ของ Curve
- PI point ของ Curve (Start + tangent ไปตามทิศ azimuth ขาเข้า)
- PI point ของ Spiral (Start + tanLong ไปตามทิศ azimuth ขาเข้า) ทั้ง SPIN และ SPOUT
- กรณี R ติดลบ (โค้งซ้าย) ว่าสูตรยังใช้ค่าเดิมได้ (ใช้ R บวกเสมอในสูตร ไม่ใช่ el.k_in ตรงๆ)

## หก — attribute `delta` ใหม่ ชนกับความหมายเดิมของ "Delta" หรือไม่

**ไม่ชนกัน เป็นคนละบริบทกันโดยสิ้นเชิง:**

1. **Delta ใน CSV (บริบทเดิม)** — คอลัมน์ `Delta`/`delta` ใน compound curve sub-row ของ
   PI table (`src/smt/builders/alignment_builder.py` บรรทัด 74-83, ใช้ใน
   `tests/builders/test_alignment_builder.py` บรรทัด 733 และ `tests/test_cli.py` บรรทัด
   106/118) เป็น **input ที่ผู้ใช้กรอกเอง** หน่วยองศา หมายถึงมุมเบี่ยงของ**บาง**ส่วนโค้งใน
   compound curve (arc แรกๆ เท่านั้น ส่วนโค้งสุดท้ายรับมุมที่เหลือแบบไม่ต้องกรอก — ดู
   `_build_curve_sub_elements` บรรทัด 74-84) ใช้ในไฟล์ `builders/alignment_builder.py`
   เท่านั้น เป็นส่วนของ**การอ่าน PI table เข้ามาสร้าง alignment**

2. **delta ใหม่ที่จะเพิ่ม (บริบทนี้)** — attribute XML บน `<Curve>` tag ตอน**ส่งออก**
   LandXML ใน `src/smt/landxml.py` เป็น**ค่าที่คำนวณเอง**จาก entry/exit azimuth ของ Curve
   element นั้นๆ (ผ่าน `_theta_rad` ที่มีอยู่แล้ว) หมายถึงมุมเบี่ยงทั้งหมดของส่วนโค้งวงกลม
   Curve element นั้นเพียงตัวเดียว (ไม่ใช่มุมของทั้ง PI ที่อาจมี spiral ประกบด้วย)

ทั้งสองอยู่คนละไฟล์ คนละฟังก์ชัน คนละทิศทางข้อมูล (อันหนึ่งเป็น input ตอน parse, อีกอันเป็น
output ตอน export) ไม่มีตัวแปรชื่อ `delta` ที่ใช้ร่วมกันข้ามสโคป และในสโคปของ
`export_alignment_landxml` เองก็ยังไม่มีตัวแปรชื่อ `delta` อยู่ก่อนเลย (ตรวจสอบแล้วในหัวข้อหนึ่ง)
จึงไม่มีความเสี่ยงชนกันทั้งในระดับโค้ดและระดับความหมาย

## สรุปสูตรที่ตรวจสอบแล้ว (ไม่ใช่ "ยืนยันแล้ว") พร้อมข้อมูลระดับผลต่างจริง

Curve (ต้องมี Δ เฉพาะของ Curve element นั้น จาก `_theta_rad(el.azimuth, exit_az)`):
- tangent  = R · tan(Δ/2)
- chord    = 2R · sin(Δ/2)
- external = R · (1/cos(Δ/2) − 1)
- midOrd   = R · (1 − cos(Δ/2))
- crvType  = "arc" (ค่าคงที่ ไม่ต้องคำนวณ)
- PI point = (Start.n + tangent·cos(el.azimuth), Start.e + tangent·sin(el.azimuth))

Spiral (SPIN และ SPOUT ทั้งคู่ ใช้ `tan_long` ที่ `_spiral_geometry` คำนวณอยู่แล้ว):
- PI point = (Start.n + tanLong·cos(el.azimuth), Start.e + tanLong·sin(el.azimuth))

ผลต่างจาก Civil 3D จริงอยู่ที่ 0.000008–0.0003 เมตร (0.008–0.30 มม.) ทุกค่า **ไม่ใช่
ตรงกันเป๊ะ** สาเหตุที่เป็นไปได้ (ยังไม่พิสูจน์ยืนยัน) คือ Civil 3D คำนวณ alignment
geometry ใหม่เองหลัง import ไม่ได้ preserve ค่าดิบ ต้องนำระดับผลต่างนี้ไปพิจารณาตอนตั้ง
tolerance ของ test ในแผนถัดไป (แนะนำ ~0.5 มม. ไม่ใช่ 1e-6)

ยังไม่ได้ออกแบบ element ordering ของ `<PI>` sub-tag ภายใน `<Curve>`/`<Spiral>` (จะวางไว้ตำแหน่ง
ไหนระหว่าง Start/Center/End) และยังไม่ได้ออกแบบ tests ใหม่จริง — ทั้งสองเรื่องนี้เก็บไว้ทำในแผน
ถัดไป (session_logs/plan_*.md) ตามข้อตกลง Plan-Review-Approve ก่อนแก้โค้ดจริง
