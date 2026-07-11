# สืบสวนสโคป Phase 4 — อัปเดต VBA COSINE ให้ตรงกับ core engine ปัจจุบัน

วันที่ 2026-07-12
ประเภทงาน สืบสวน/รายงานเท่านั้น ยังไม่แก้ไฟล์ VBA ใดๆ ทั้งสิ้น

บริบท `src/smt/alignment.py` ผ่านการแก้สูตร COSINE สะสมมา 3 รอบ นับตั้งแต่ VBA
(`reference/vba/SMT_Core.bas`, `reference/vba/SMT_Alignment.bas`) ถูกพอร์ตครั้งล่าสุด:
1. สูตรปิด Civil 3D Sine Half-Wavelength (แทนสูตร curvature-vs-arc-length แบบเดียวกับ
   CLOTHOID/BLOSS/SINE) — แก้เมื่อ 2026-07-05
2. `_build_curve_sub_elements` แก้ turning angle ใน **builder** เท่านั้น (ไม่ใช่
   point-on-element ของ alignment.py จึงไม่กระทบ SMT_Alignment.bas)
3. arc-length inversion ผ่าน Simpson quadrature + bisection + `lru_cache`
   (Phase 1, commit `d8ebedd`) แทนค่าประมาณเดิม `a ≈ d/X`

---

## 1. โค้ด VBA COSINE ปัจจุบัน (เต็มทุกจุด)

**`SMT_ShapeIntegral` — `reference/vba/SMT_Alignment.bas:56-69`:**
```vba
Private Function SMT_ShapeIntegral(transition As String, tau As Double) As Double
    Dim PI As Double
    PI = SMT_Pi()
    Select Case UCase(Trim(transition))
        Case "BLOSS"
            SMT_ShapeIntegral = tau ^ 3# - tau ^ 4# / 2#
        Case "COSINE"
            SMT_ShapeIntegral = tau / 2# - Sin(PI * tau) / (2# * PI)
        Case "SINE"
            SMT_ShapeIntegral = tau ^ 2# / 2# - (1# - Cos(2# * PI * tau)) / (4# * PI ^ 2#)
        Case Else  ' CLOTHOID (default): f(tau)=tau -> F(tau)=tau^2/2
            SMT_ShapeIntegral = tau ^ 2# / 2#
    End Select
End Function
```

**`SMT_TurningAngle` — `SMT_Alignment.bas:77-86`** (เรียก `SMT_ShapeIntegral` แบบเดียวกันทุก transition):
```vba
Private Function SMT_TurningAngle(kIn As Double, kOut As Double, L As Double, _
                                   transition As String, s As Double) As Double
    Dim tau As Double
    If L = 0# Then
        SMT_TurningAngle = kIn * s
    Else
        tau = s / L
        SMT_TurningAngle = kIn * s + (kOut - kIn) * L * SMT_ShapeIntegral(transition, tau)
    End If
End Function
```

**`SMT_PointOnElement` ส่วน spiral — `SMT_Alignment.bas:157-183`** (Simpson 48 ช่วง เหมือนกันทุก transition ไม่มี COSINE-specific branch):
```vba
Else
    ' Spiral: Simpson integration in local frame (x=along entry tangent, y=left)
    nSeg = SMT_SPIRAL_STEPS
    h = d / CDbl(nSeg)
    sumX = 0#
    sumY = 0#
    For i = 0 To nSeg
        s = CDbl(i) * h
        th = SMT_TurningAngle(kIn, kOut, L, transition, s)
        If i = 0 Or i = nSeg Then
            w = 1
        ElseIf (i Mod 2) = 1 Then
            w = 4
        Else
            w = 2
        End If
        sumX = sumX + CDbl(w) * Cos(th)
        sumY = sumY + CDbl(w) * Sin(th)
    Next i
    x = sumX * h / 3#
    y = sumY * h / 3#
    ca = Cos(az0)
    sa = Sin(az0)
    res(0) = n0 + x * ca - y * sa
    res(1) = e0 + x * sa + y * ca
    res(2) = SMT_NormalizeAngle(az0 + SMT_TurningAngle(kIn, kOut, L, transition, d))
End If
```

**สรุป**: VBA ไม่มี branch พิเศษสำหรับ COSINE เลย — ใช้กลไก Simpson integration แบบ
curvature-vs-arc-length เดียวกับ CLOTHOID/BLOSS/SINE ทุกประการ ผ่าน `SMT_ShapeIntegral`
case "COSINE" ด้านบน `SMT_Core.bas` ไม่มีโค้ดเกี่ยวกับ COSINE เลยแม้แต่บรรทัดเดียว
(ตรวจแล้วด้วย grep)

---

## 2. เทียบเวอร์ชันกับ Python ปัจจุบัน (หลัง commit `d8ebedd`)

Python ปัจจุบัน (`src/smt/alignment.py:378-401`) มี branch พิเศษดักจับ COSINE ที่เป็น
pure SPIN/SPOUT (`(el.k_in == 0) != (el.k_out == 0)`) แล้วเรียกสูตรปิด Civil 3D
Sine Half-Wave ผ่าน `_sine_halfwave_point` ซึ่งใช้ arc-length inversion
(`_cosine_solve_a`) แทนการเรียก `_shape_integral`/Simpson-over-θ เดิม

**สรุปตรงไปตรงมา: VBA ตอนนี้ตรงกับเวอร์ชัน Python "ก่อน commit ทั้งสามรอบ" คือ
ก่อนแม้แต่ COSINE closed-form fix รอบแรก (2026-07-05)** ไม่ใช่แค่ตกรอบ arc-length
inversion (Phase 1) เท่านั้น — VBA ตกทั้ง 2 รอบที่เกี่ยวข้องกับไฟล์นี้
(รอบ 2 คือ `_build_curve_sub_elements` เป็นการแก้ใน builder ไม่ใช่ point-on-element
จึงไม่นับเป็นรอบที่กระทบ SMT_Alignment.bas)

---

## 3. ขนาดผลกระทบจริง (อ้างอิงตัวเลขที่มีอยู่แล้ว)

### 3.1 ผลจากการไม่มีสูตรปิด (fix รอบ 1) — ผลกระทบหลัก ระดับเซนติเมตร

จาก `session_logs/plan_cosine_sinehalfwave_fix.md` / CLAUDE.md known-limits: สูตร
Simpson-integral เดิม (ที่ VBA ยังใช้อยู่ตอนนี้) คลาดเคลื่อนเทียบ Civil 3D จริง
**~2.90 ซม.** ที่ R=900, L=100 และ **~4.71 ซม.** ที่ R=250, L=50
(tanLong/tanShort) — เป็น error ก้อนใหญ่ที่สุด เพราะกลไกทางคณิตศาสตร์ผิดตั้งแต่ต้น
(นิยาม curvature-vs-arc-length ทั้งที่ Civil 3D นิยามด้วย tangent-projected-distance)

### 3.2 ผลจากการไม่มี arc-length inversion (fix รอบ 3) — ผลกระทบรอง ระดับมิลลิเมตร

จาก `session_logs/investigate_sinehalfwave_formula.md` (บรรทัดท้าย): ถ้าใช้สูตรปิด
แล้วแต่ยังประมาณ `a ≈ d/X` (แทนที่จะ invert arc-length integral จริง) ที่จุด d=L:
- R=900, L=100 (L−X = 0.027986 m): theta คลาดเคลื่อน **0.00178°**, totalY คลาดเคลื่อน
  **1.5548 มม.**
- R=250, L=50 (L−X = 0.045338 m): theta คลาดเคลื่อน **0.01029°**, totalY คลาดเคลื่อน
  **4.5338 มม.**

จาก `session_logs/investigate_cosine_arclength_inversion.md`: เมื่อแก้ด้วย
arc-length inversion (bisection หา a จาก s(a)=d จริง) แทนค่าประมาณ ผลลัพธ์ดีขึ้นมาก:
- R=900/L=100: theta diff เหลือ **2.27e-06°**
- R=250/L=50: theta diff เหลือ **4.23e-05°**
- R=500/L=70 (จุดที่ 3): ค่าประมาณเดิม (a=L/X) คลาดเคลื่อน **0.003546624°** เทียบ
  a=1 exact ส่วน bisection เหลือ **7.178e-06°** — ดีขึ้นประมาณ **494 เท่า**

**สรุป**: error รวมของ VBA ปัจจุบันเทียบ Civil 3D ถูกครอบงำโดย error ระดับ 3-5 ซม.
จากการไม่มีสูตรปิดเลย (ข้อ 3.1) ส่วน error ระดับมิลลิเมตรจากการไม่มี arc-length
inversion (ข้อ 3.2) เป็นก้อนรองที่จะปรากฏหลังแก้สูตรปิดแล้วเท่านั้น

---

## 4. ความซับซ้อนของการ port arc-length inversion ไป VBA

### 4.1 Cache เทียบเท่า `lru_cache`
**ไม่มี** กลไก memoization ในตัว VBA เลย grep หา `Dictionary`/`Simpson`/`bisection`/
`SPIRAL_STEPS` ทั่ว `reference/vba/*.bas` ไม่พบนอกเหนือจาก `SMT_Alignment.bas` เอง
ถ้าจะทำ cache แบบเดียวกับ Python's `_cosine_arc_length_table`
(`@lru_cache(maxsize=256)` keyed ด้วย `(length, r_abs)`) ต้องออกแบบเอง เช่นใช้
module-level `Scripting.Dictionary` คีย์เป็น string ผสม length กับ r_abs — **นี่เป็น
pattern ใหม่ทั้งหมด ไม่มีตัวอย่างในโค้ดเบสนี้เลย** เป็นจุดตัดสินใจเชิงออกแบบที่ต้อง
รอแผนแก้จริงตัดสินใจ ไม่ตัดสินใจในรายงานนี้

### 4.2 Pattern ที่มีอยู่แล้วในไฟล์เดียวกัน — ลดความเสี่ยงลงมาก
- **Simpson quadrature 48 ช่วง**: มีอยู่แล้วใน `SMT_PointOnElement:158-177`
  (ใช้กับ cos θ/sin θ) — เทคนิคเดียวกันเป๊ะ แค่เปลี่ยน integrand เป็น
  `X*sqrt(1+(dy/dx)^2)` เท่านั้น
- **Bisection 50 รอบ**: มีอยู่แล้วใน `SMT_ProjectOnElement:267-289`
  (`' Spiral: bisection on g(s) = (P - Q(s)) . tangentDir(s) = 0`) —
  รูปแบบเดียวกับที่ Python ใช้ทั้งใน `calculate_projection_to_element` และ
  `_cosine_solve_a`

**สรุป**: ทั้ง Simpson และ bisection ซึ่งเป็นแกนหลักของ arc-length inversion
**มีต้นแบบพิสูจน์แล้วอยู่ในไฟล์นี้เอง** งาน port จึงเป็นการ "เอาเทคนิคเดียวกันไปใช้กับ
integrand ใหม่" ไม่ใช่การคิดค้นกลไกเชิงตัวเลขใหม่ในภาษา VBA ความเสี่ยงด้านนี้ต่ำ
ส่วนที่เหลือความเสี่ยงจริงคือข้อ 4.1 (cache) เท่านั้น

---

## 5. Test suite / กลไกยืนยันความถูกต้องของ VBA

**ไม่มี automated test harness สำหรับ VBA เลย** (ไม่มี "AllTests" analog แบบ oracle .gs)
กลไกเดียวที่มีคือ comment block "Expected values" ท้ายไฟล์ เช่น
`SMT_Alignment.bas:584-597`:
```
'   SMT_StaToN(0, 0, SMT_Elements)                  = 1568000.0
'   SMT_StaToE(519.615, 0, SMT_Elements)             = 678519.615
'   SMT_CoordToSta(1568000, 678000, SMT_Elements)    = 0.0
'   SMT_CoordToOffset(1568000, 678000, SMT_Elements) = 0.0
'   SMT_WCBatSta(0, SMT_Elements) = 90.0
```
เป็นค่าที่เทียบกับ Python มือครั้งเดียวตอน port ไม่มีจุดข้อมูล COSINE โดยเฉพาะ
ใน comment block ปัจจุบัน `reference/vba/README.md` ก็มีแค่ module map/signature/
ตัวอย่างการใช้งาน ไม่มีกลไก test ใดๆ ค้นทั่ว `reference/` ไม่พบไฟล์ที่ชื่อเกี่ยวกับ
test สำหรับ VBA เลย มีแค่ `SMT_Calcuator.xlsm` ซึ่งเป็น example workbook ไม่ใช่
test harness

**แนวทางยืนยันที่ต้องใช้เมื่อแก้จริง**: ต้องเปิด Excel จริง (ตามกฎ CLAUDE.md ข้อ 4.3)
ป้อนค่าจาก 3 จุด Civil 3D ground truth เดิมที่ใช้ยืนยัน Python แล้ว
(R=900/L=100, R=250/L=50, R=500/L=70) แล้วอัปเดต comment block ให้ตรงกับค่าที่ verify
ได้จริง ไม่มี regression safety net แบบ golden-fixture JSON เหมือนฝั่ง Python

---

## 6. ขอบเขตงานจริง (blast radius)

Grep `SMT_ShapeIntegral`/`SMT_TurningAngle`/`COSINE`/`SMT_Alignment`/`SMT_Core.`
ใน `SMT_Vertical.bas`, `SMT_Crossfall.bas`, `SMT_Geometry.bas` — **ไม่พบสักจุดเดียว**
ตรงกับ dependency diagram ใน README.md ที่ระบุว่า `SMT_Vertical`/`SMT_Crossfall`
ไม่ผูกกับโมดูลอื่นเลย ส่วน `SMT_Geometry` ผูกกับ `SMT_Core` แค่ฟังก์ชัน angle/coordinate
พื้นฐาน (`SMT_DegToRad`, azimuth) ไม่เกี่ยวกับ spiral/COSINE logic

**สรุปขอบเขต: (ก) แก้เฉพาะ `SMT_Alignment.bas` เท่านั้น** — เพิ่ม private helper
ใหม่ราว 5 ฟังก์ชัน (mirror `calculate_sine_halfwave_tangent_length`,
`_cosine_dydx`, `_cosine_arc_length`, `_cosine_arc_length_table`,
`_cosine_solve_a`, `_sine_halfwave_point`) บวก branch ใหม่ใน `SMT_PointOnElement`
ก่อนถึง Simpson path เดิม (mirror `alignment.py:378-401`)
- `SMT_ShapeIntegral` case "COSINE" (บรรทัด 62-63) **ไม่ต้องแก้** — เก็บไว้เป็น
  fallback สำหรับกรณี compound spiral ที่ยังไม่รองรับ ตรงกับที่ Python เก็บ
  `_shape_integral`'s COSINE case ไว้เหมือนกันด้วยเหตุผลเดียวกัน
- `SMT_Core.bas`, `SMT_Vertical.bas`, `SMT_Crossfall.bas`, `SMT_Geometry.bas`
  **ไม่ต้องแก้เลย**
- `SMT_ProjectOnElement` **ไม่ต้องแก้แยก** — เรียก `SMT_PointOnElement` เป็น
  black box อยู่แล้ว (ตรงกับ Python ที่ `calculate_projection_to_element`
  เรียก `calculate_point_on_element` ภายใน bisection loop ของมันเอง ที่
  `alignment.py:504-506`) แก้ `SMT_PointOnElement` แล้วฝั่ง inverse ได้ผลถูกต้อง
  ไปด้วยโดยอัตโนมัติ

**ไม่ใช่ (ข)** — ไม่กระทบไฟล์ VBA อื่นนอกเหนือจาก `SMT_Alignment.bas`

---

## 7. ประเมินขนาดงานเทียบ Phase 1 ของ Python

Python Phase 1 (`session_logs/plan_cosine_arclength_core_fix.md`, commit `d8ebedd`)
แก้ `alignment.py` เพิ่มฟังก์ชัน/ค่าคงที่ใหม่ราว 5 รายการ (~90 บรรทัด) บวก
regenerate golden fixture 2 ไฟล์ (`tests/golden/tables.json`,
`reference/tables.json`) บวกเพิ่ม regression test

VBA Phase 4 ที่ประเมิน: แก้ไฟล์เดียว (`SMT_Alignment.bas`) เพิ่ม private helper
ราว 5 ฟังก์ชัน (~80-100 บรรทัด VBA) ขนาดใกล้เคียงกัน แต่มีจุดที่ **ง่ายกว่า** และ
**ยากกว่า** สลับกันไป:

**ง่ายกว่า:**
- ไม่ต้อง regenerate golden fixture (VBA ไม่มี automated test suite/JSON fixture
  ให้ regenerate)
- เทคนิคเชิงตัวเลข (Simpson, bisection) มีต้นแบบพิสูจน์แล้วในไฟล์เดียวกัน
  ไม่ต้องคิดค้นใหม่ ความเสี่ยงด้านสูตรต่ำ เพราะ Python แก้และยืนยันสูตรให้แล้ว
  งานที่เหลือคือการแปลภาษาเป็นหลัก

**ยากกว่า:**
- ต้องออกแบบ cache pattern ใหม่ (`Scripting.Dictionary`) ที่ไม่มีต้นแบบในโค้ดเบสนี้
  เลย รวมถึงพิจารณา lifetime ของ Dictionary ข้าม UDF call ภายใน Excel session
- การยืนยันผลเป็น manual-Excel-only ไม่มี regression safety net แบบ pytest
  ต้องเปิด Excel จริงทุกครั้งที่แก้ตามกฎ CLAUDE.md ข้อ 4.3

**สรุปขนาดงาน: ใกล้เคียงกับ Phase 1 ของ Python ในแง่ปริมาณโค้ด (order of magnitude
เดียวกัน) ไม่เล็กกว่าและไม่ใหญ่กว่าอย่างมีนัยสำคัญ** แต่ลักษณะความเสี่ยงต่างกัน —
Python Phase 1 ความเสี่ยงหลักอยู่ที่ "คิดสูตรให้ถูก" (แก้ไปแล้ว) ส่วน VBA Phase 4
ความเสี่ยงหลักอยู่ที่ "ออกแบบ cache pattern ใหม่ + ยืนยันด้วยมือใน Excel จริง"

---

## สรุปรวม

ยังไม่มีการเขียนแผนแก้ไฟล์ VBA ใดๆ ในรอบนี้ตามคำสั่งของผู้ใช้ รายงานนี้ระบุแค่ข้อเท็จจริง
และประเมินขนาดงานเท่านั้น รอ Plan-Review-Approve รอบใหม่ก่อนลงมือแก้ `SMT_Alignment.bas`
จริง
