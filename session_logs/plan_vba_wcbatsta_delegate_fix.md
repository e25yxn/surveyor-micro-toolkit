# แผนแก้ SMT_WCBatSta ให้ delegate ผ่าน SMT_SolveForward/SMT_PointOnElement (Option B)

วันที่ 2026-07-12
ประเภทงาน แผนแก้โค้ด ยังไม่แก้ไฟล์ใดๆ ทั้งสิ้น รอ Plan-Review-Approve

บริบท ทดสอบ Excel จริงหลัง Phase 4 พบว่า `SMT_WCBatSta` คำนวณ theta ผิดสำหรับ COSINE
(ได้ 3.18309886183791° แทนที่จะเป็น 3.178942°) ตรวจสอบแล้วว่า `SMT_WCBatSta`
(`reference/vba/SMT_Alignment.bas:624-702`) เป็นฟังก์ชันแยกที่เขียนสูตรเชิงมุมเอง
(`d²/(2RL)` สำหรับ SPIN, `d/R − d²/(2RL)` สำหรับ SPOUT) ไม่เคยเรียก
`SMT_PointOnElement` เลย และไม่อ่านคอลัมน์ Transition เลยด้วยซ้ำ — บั๊กนี้จึงไม่ใช่แค่
ผลกระทบจาก Phase 4 แต่เป็นบั๊กเดิมที่มีมาก่อนหน้านั้นแล้วสำหรับ BLOSS/SINE ที่จุดกลางโค้ง
เช่นกัน (แค่บังเอิญตรงกันที่ปลายทั้งสองข้าง เพราะทุก shape มี F(1)=0.5 เท่ากันหมด)
แผนนี้แก้ให้ `SMT_WCBatSta` delegate ไปที่ engine เดียวกับ `SMT_StaToN`/`SMT_StaToE`
แทนการมีสูตรมุมแยกซ้ำ

---

## หนึ่ง — เปิด `SMT_SolveForward` เต็มฟังก์ชัน ตรวจ index ของ pt array

```vba
Private Function SMT_SolveForward(sta As Double, offset As Double, _
                                   rng As Range) As Variant
    Dim nRows As Long, i As Long
    Dim staStart As Double, staEnd As Double
    Dim n0 As Double, e0 As Double
    Dim azDeg As Double, az0 As Double
    Dim radius As Double, typStr As String, transStr As String
    Dim kIn As Double, kOut As Double, L As Double, d As Double
    Dim pt As Variant, offAz As Double
    Dim res(1) As Double

    nRows = rng.Rows.Count
    For i = 1 To nRows
        staStart = CDbl(rng.Cells(i, 1).Value)
        staEnd = CDbl(rng.Cells(i, 2).Value)
        If sta >= staStart - SMT_STA_TOL And sta <= staEnd + SMT_STA_TOL Then
            n0 = CDbl(rng.Cells(i, 3).Value)
            e0 = CDbl(rng.Cells(i, 4).Value)
            azDeg = CDbl(rng.Cells(i, 5).Value)
            az0 = SMT_DegToRad(azDeg)
            radius = CDbl(rng.Cells(i, 6).Value)
            typStr = CStr(rng.Cells(i, 7).Value)
            transStr = CStr(rng.Cells(i, 8).Value)
            If Len(Trim(transStr)) = 0 Then transStr = "CLOTHOID"
            kIn = 0#
            kOut = 0#
            SMT_GetCurvatures typStr, radius, kIn, kOut
            L = staEnd - staStart
            d = sta - staStart
            If d < 0# Then d = 0#
            pt = SMT_PointOnElement(n0, e0, az0, kIn, kOut, L, transStr, d)
            If offset <> 0# Then
                offAz = SMT_NormalizeAngle(pt(2) + SMT_Pi() / 2#)
                res(0) = pt(0) + offset * Cos(offAz)
                res(1) = pt(1) + offset * Sin(offAz)
            Else
                res(0) = pt(0)
                res(1) = pt(1)
            End If
            SMT_SolveForward = res
            Exit Function
        End If
    Next i
    SMT_SolveForward = CVErr(xlErrValue)
End Function
```

**สำคัญ — พบว่าสมมติฐานในคำสั่งงานคลาดเคลื่อน**: `pt` (ตัวแปรภายในที่ได้จาก
`SMT_PointOnElement`) มี 3 element จริง (`pt(0)`=N, `pt(1)`=E, `pt(2)`=tangent
azimuth) แต่ **`SMT_SolveForward` เองคืนค่าแค่ 2 element** (`Dim res(1) As Double`
→ index 0,1 เท่านั้น) — `res(2)` ไม่มีอยู่เลย ฟังก์ชันทิ้งค่า `pt(2)` (azimuth) ไปเฉยๆ
ทุกครั้งที่เรียก ไม่ได้ propagate ออกมา ดังนั้น `SMT_WCBatSta` **เรียก
`SMT_SolveForward` แล้วอ่าน index 2 ตรงๆ ไม่ได้** ต้องแก้ `SMT_SolveForward`
เองด้วย ให้คืนค่า azimuth เป็น element ที่ 3 ก่อน — งานจึงมี **2 จุดที่ต้องแก้** ไม่ใช่
จุดเดียว:
1. `SMT_SolveForward`: ขยาย `res` จาก `Dim res(1) As Double` เป็น
   `Dim res(2) As Double` แล้วเพิ่ม `res(2) = pt(2)` (เก็บ tangent azimuth เสมอ
   ไม่ว่า offset จะเป็น 0 หรือไม่ก็ตาม เพราะ tangent azimuth ของจุดกึ่งกลางเส้น
   ไม่เปลี่ยนตาม offset ที่เยื้องออกมา — ตรงกับที่ `SMT_WCBatSta` ไม่เคยรับ
   offset parameter อยู่แล้ว จะเรียกด้วย offset=0 เสมอ)
2. `SMT_WCBatSta`: เปลี่ยนจากสูตรมุมเองทั้งหมด เป็นเรียก
   `SMT_SolveForward(sta, 0#, rng)` แล้วอ่าน `pt(2)`

**grep ยืนยันแล้ว**: `SMT_SolveForward` มีผู้เรียกแค่ 2 จุดในทั้งไฟล์
(`SMT_StaToN` บรรทัด 552, `SMT_StaToE` บรรทัด 572) ทั้งสองอ่านแค่ `pt(0)`/`pt(1)`
ไม่แตะ `pt(2)` เลย — เพิ่ม element ที่ 3 เข้าไปจึง **ปลอดภัย ไม่กระทบผู้เรียกเดิม**

---

## สอง — ออกแบบ diff

### 2.1 `SMT_SolveForward` — เพิ่ม `res(2)`

```vba
    Dim pt As Variant, offAz As Double
    Dim res(2) As Double   ' was: Dim res(1) As Double
```
และหลัง `If offset <> 0# Then ... Else ... End If`:
```vba
            If offset <> 0# Then
                offAz = SMT_NormalizeAngle(pt(2) + SMT_Pi() / 2#)
                res(0) = pt(0) + offset * Cos(offAz)
                res(1) = pt(1) + offset * Sin(offAz)
            Else
                res(0) = pt(0)
                res(1) = pt(1)
            End If
            res(2) = pt(2)   ' NEW: tangent azimuth, independent of offset
```
Docstring comment (บรรทัด 434-437) ต้องแก้ด้วย: `Returns Variant Array (0)=N
(1)=E (2)=tangentAzimuth(rad), or CVErr(xlErrValue) if sta out of range.`

### 2.2 `SMT_WCBatSta` — เขียนใหม่ทั้งฟังก์ชัน

```vba
Public Function SMT_WCBatSta(sta As Double, rng As Range) As Variant
    ' WCB (whole-circle bearing / azimuth) of the alignment centre-line tangent
    ' at station sta, in decimal degrees, normalised to [0, 360).
    '
    ' Delegates to SMT_SolveForward/SMT_PointOnElement -- the same engine
    ' SMT_StaToN/SMT_StaToE use -- instead of a separate hand-written angle
    ' formula. The previous formula (theta=d^2/(2*R*L) for SPIN, theta=d/R -
    ' d^2/(2*R*L) for SPOUT) ignored the Transition column entirely: exactly
    ' correct for CLOTHOID only, silently wrong for BLOSS/SINE at interior
    ' stations, and wrong for COSINE everywhere except the two endpoints
    ' (where every transition shape's turning-angle integral coincidentally
    ' equals the same value). See
    ' session_logs/plan_vba_wcbatsta_delegate_fix.md.
    '
    ' sta : arc distance along alignment (metres).
    ' rng : SMT_Elements Named Range -- 8 columns, no header row.
    '       col5 Azimuth must be decimal degrees; converted to rad internally.
    ' Returns #VALUE! when sta is outside all elements.
    Dim pt As Variant
    pt = SMT_SolveForward(sta, 0#, rng)
    If IsError(pt) Then
        SMT_WCBatSta = pt
    Else
        SMT_WCBatSta = SMT_RadToDeg(SMT_NormalizeAngle(pt(2)))
    End If
End Function
```

Signature unchanged (`sta As Double, rng As Range`, returns `Variant`), error
path unchanged (`CVErr(xlErrValue)` propagates straight through from
`SMT_SolveForward`, identical constant to the old `CVErr(xlErrValue)` at the
old function's own end).

---

## สาม — ผลกระทบต่อ public API

- **Signature**: ไม่เปลี่ยน (`SMT_WCBatSta(sta As Double, rng As Range) As
  Variant`) — คงเดิมทุกประการ
- **Error handling**: `SMT_SolveForward` คืน `CVErr(xlErrValue)` เมื่อไม่พบ
  element ใดครอบคลุม `sta` (บรรทัด 482, ค่าคงที่เดียวกับที่ `SMT_WCBatSta` เดิมใช้
  ที่บรรทัด 705) — ผ่าน `IsError(pt)` แล้ว forward ค่า error object ตรงๆ ตรงแบบ
  เดียวกับที่ `SMT_StaToN`/`SMT_StaToE` ทำอยู่แล้วทุกประการ (บรรทัด 553-554,
  573-574) — behavior เดิมคงอยู่ครบ
- **Caller เดิม**: grep ทั้ง `reference/vba/*.bas` พบว่าไม่มีฟังก์ชัน VBA ใดเรียก
  `SMT_WCBatSta` จากภายในเลย (พบแค่ชื่อในคอมเมนต์/README ตัวอย่างการใช้งานจาก
  worksheet เท่านั้น) — ไม่มี internal caller ที่ต้องกังวลเรื่อง behavior เปลี่ยน
- **จุดที่ behavior เปลี่ยนจริง แม้ผลลัพธ์ตัวเลขจะเหมือนเดิมในทางปฏิบัติ (ต้องบันทึกไว้
  ตรงๆ ไม่ปิดบัง)**:
  1. **Tolerance ที่ station boundary**: `SMT_WCBatSta` เดิมไม่มี tolerance เลย
     (`sta >= staStart And (sta < staEnd Or ...)` ตรงเป๊ะ) ส่วน `SMT_SolveForward`
     ใช้ `SMT_STA_TOL = 0.0001` (0.1mm) ทั้งสองข้าง — เวอร์ชันใหม่ **ผ่อนปรนกว่าเดิม**
     (รับ sta ที่คลาดเคลื่อนจากขอบเขต element ไม่เกิน 0.1mm ได้ ซึ่งเดิมจะ error) เป็น
     backward-compatible (ไม่ทำให้ค่าที่เคยได้ผลลัพธ์ถูกต้องกลับกลายเป็น error)
  2. **การเลือก element ที่ station ต่อกันพอดี** (เช่น sta ตรงกับ StaEnd ของ element i
     พอดี ซึ่งเท่ากับ StaStart ของ element i+1 พอดี): `SMT_WCBatSta` เดิมใช้เงื่อนไข
     `sta < staEnd` (ยกเว้นแถวสุดท้าย) ทำให้ตกไปแมตช์ element ถัดไปเสมอที่ขอบ (คำนวณ
     azimuth จาก d=0 ของ element i+1) ส่วน `SMT_SolveForward` วนลูปแล้ว
     `Exit Function` ทันทีที่เจอแถวแรกที่ match (ใช้ `<=` ทั้งสองข้าง) ทำให้ตกไปแมตช์
     element ก่อนหน้าแทนที่ขอบ (คำนวณจาก d=L ของ element i) — **ต่างกันที่ว่าใช้
     element ไหน แต่ตัวเลข azimuth ที่ได้ควรเท่ากันเป๊ะสำหรับ chain ที่ไม่มี gap**
     (exit azimuth ของ element i ต้องเท่ากับ entry azimuth ของ element i+1 พอดี
     ตามที่ `test_chain_has_no_gaps`/`test_exit_state_matches_next_entry` ฝั่ง Python
     บังคับไว้แล้ว) — ต้องระบุไว้ตรงๆ ว่าเป็นความต่างเชิงกลไก ไม่ใช่ตัวเลขต่าง แต่ควร
     มี test เจาะจงจุดต่อ element ยืนยันว่าไม่ต่างจริงก่อน apply

---

## สี่ — พิสูจน์ความเท่ากันทางคณิตศาสตร์สำหรับ T, C, SPIN/SPOUT-CLOTHOID (ก่อน apply)

**T (tangent)**: สูตรเดิม `theta_rad = 0`. Engine ใหม่: `SMT_PointOnElement`
กิ่ง tangent คืน `res(2) = az0` ตรงๆ (ไม่บวก theta เลย) → เท่ากับ `azDeg` เดิม
บวก 0 พอดี **เท่ากันทุกกรณี ไม่มีเงื่อนไข**

**C (circular)**: สูตรเดิม `theta_rad = d / radius`. Engine ใหม่: กิ่ง circular
`k = kIn` (ซึ่ง `SMT_GetCurvatures` ตั้งเป็น `k = 1/radius` สำหรับ type "C"),
`theta = k * d = d / radius` — **สูตรเดียวกันตัวต่อตัว** (`k*d` เทียบเท่า `d/radius`
พีชคณิตตรงๆ เพราะ `k=1/radius`) ไม่ใช่แค่ตัวเลขบังเอิญตรงกัน

**SPIN-CLOTHOID**: สูตรเดิม `theta_rad = d² / (2·R·L)`. Engine ใหม่: กิ่ง COSINE
ไม่ trigger (transition≠COSINE) ตกไปกิ่ง spiral ทั่วไป เรียก `SMT_TurningAngle`
ซึ่งสำหรับ CLOTHOID ใช้ `SMT_ShapeIntegral` case Else: `F(τ)=τ²/2` ดังนั้น
`theta = kIn·d + (kOut−kIn)·L·F(d/L) = 0 + (1/R)·L·(d/L)²/2 = (1/R)·L·d²/(L²·2)
= d²/(2·R·L)` — **พีชคณิตเท่ากันเป๊ะ** กับสูตรเดิม (สูตรเดียวกัน จัดกลุ่มพจน์ต่างกัน
เท่านั้น ไม่ใช่ approximation คนละตัว)

**SPOUT-CLOTHOID**: สูตรเดิม `theta_rad = d/R − d²/(2·R·L)`. Engine ใหม่:
`theta = kIn·d + (kOut−kIn)·L·F(d/L) = d/R + (0−1/R)·L·(d/L)²/2 = d/R −
d²/(2·R·L)` — **พีชคณิตเท่ากันเป๊ะ** เช่นกัน

สรุป: สำหรับ 4 กรณีเดิมที่ `SMT_WCBatSta` เคยรองรับถูกต้องอยู่แล้ว (T, C, SPIN/
SPOUT ที่เป็น CLOTHOID) สูตรใหม่ให้ค่าที่เท่ากันทางพีชคณิต ต่างกันแค่ระดับ
floating-point rounding จากลำดับการคำนวณที่ต่างกันเท่านั้น (ยืนยันเชิงตัวเลขแล้วด้วย
Python เทียบสูตรเก่ากับ engine จริงที่ d=0 และ d=L ของ CLOTHOID R=400/L=60:
ตรงกันถึง 1e-14 หรือดีกว่า — ดูตารางในหัวข้อห้า)

---

## ห้า — ค่าทดสอบเพิ่มเติมสำหรับ BLOSS/SINE ที่จุดกลางโค้ง (พิสูจน์บั๊กเดิมและการแก้)

คำนวณจาก Python engine จริงตอนนี้ (R=400/L=60 สำหรับ BLOSS, R=500/L=70 สำหรับ
SINE — ค่าเดียวกับที่เคยใช้ยืนยัน Python Phase 1 ใน
`session_logs/plan_cosine_arclength_core_fix.md` Group 4) ตั้ง element แถวเดียว
`StaStart=0, StaEnd=length, N=0, E=0, Azimuth=90, Radius=R, Type=SPIN,
Transition=BLOSS หรือ SINE`:

| Transition | R | L | d | สูตรเก่า (บั๊ก) WCB° | Engine จริง (ถูกต้อง) WCB° | diff |
|---|---|---|---|---|---|---|
| BLOSS | 400 | 60 | 0.0 | 90.0 | 90.0 | 0 |
| BLOSS | 400 | 60 | 15.0 | 90.26857396646757 | 90.11750111032958 | **0.151°** |
| BLOSS | 400 | 60 | 30.0 | 91.0742958658703 | 90.8057218994027 | **0.269°** |
| BLOSS | 400 | 60 | 45.0 | 92.41716569820817 | 92.26609284207015 | **0.151°** |
| BLOSS | 400 | 60 | 60.0 | 94.29718346348118 | 94.29718346348119 | ~1e-14 (endpoint match) |
| SINE | 500 | 70 | 0.0 | 90.0 | 90.0 | 0 |
| SINE | 500 | 70 | 17.5 | 90.25066903536974 | 90.04748436844056 | **0.203°** |
| SINE | 500 | 70 | 35.0 | 91.00267614147894 | 90.59630680762065 | **0.406°** |
| SINE | 500 | 70 | 52.5 | 92.25602131832761 | 92.05283665139845 | **0.203°** |
| SINE | 500 | 70 | 70.0 | 94.01070456591576 | 94.01070456591577 | ~1e-14 (endpoint match) |

ยืนยันชัดเจน: ที่จุดกลางโค้ง (d≠0, d≠L) สูตรเก่าคลาดเคลื่อน 0.15–0.41° (ไม่ใช่
floating-point noise) ส่วนที่ปลายทั้งสองข้าง (d=0, d=L) ตรงกันเป๊ะ ยืนยันสมมติฐานที่
ตั้งไว้ว่า "บังเอิญตรงกันแค่ปลาย เพราะ F(1)=0.5 เหมือนกันทุก shape" **หลัง apply
diff แล้วต้องทดสอบทั้ง 10 จุดนี้ใน Excel จริง เพิ่มเติมจาก 3 จุด COSINE เดิมของ
Phase 4** (รวมเป็น 13 จุดทดสอบทั้งหมด)

---

## หก — อัปเดต docstring

ย่อหน้าคอมเมนต์เดิมของ `SMT_WCBatSta` (บรรทัด 625-642) ที่อธิบายสูตร
`theta = d²/(2RL)` ฯลฯ ต้องลบทิ้งทั้งหมด แทนที่ด้วยคำอธิบายว่าตอนนี้ delegate ไปที่
`SMT_SolveForward` (ร่างอยู่ในหัวข้อ 2.2 ด้านบนแล้ว) — ต้องระบุด้วยว่าเหตุผลที่แก้คือ
สูตรเดิมไม่อ่านคอลัมน์ Transition เลย ไม่ใช่แค่ "COSINE ผิด" เฉยๆ

---

## เจ็ด — เงื่อนไข commit

**ห้าม commit จนกว่าจะทดสอบผ่านครบทั้ง 14 จุดใน Excel จริง**: 3 จุด COSINE เดิม
(R=900/L=100, R=250/L=50, R=500/L=70 — ทดสอบ `SMT_WCBatSta` ซ้ำอีกรอบ เพราะ
ครั้งก่อนพบว่าผิด) บวก 10 จุด BLOSS/SINE ใหม่ในหัวข้อห้า บวก 1 จุดทดสอบ boundary
ด้านล่าง บวกควรสุ่มทดสอบ T, C, SPIN/SPOUT-CLOTHOID อย่างน้อยจุดละ 1-2 จุดเพื่อ
ยืนยันข้อพิสูจน์ในหัวข้อสี่ด้วยตาจริงใน Excel (ไม่ใช่แค่เชื่อพีชคณิต)

### จุดทดสอบ boundary (ยืนยันด้วยตัวเลขจริง ไม่ใช่แค่คำอธิบาย)

ใช้ `test_data/SettingOutTest.csv` ของจริงในโปรเจกต์ สร้างผ่าน pipeline จริง
(`parse_pi_table` → `build_alignment_from_pi`) พบว่า element 11 (`SPIN COSINE`,
R=500 L=70) จบพอดีที่ element 12 (`C`, CLOTHOID) เริ่ม — คือรอยต่อ SC เดียวกับ
กลุ่มโค้ง R=500/L=70 ที่เคยแก้ปิดสนิทแล้วใน Phase 3
(`session_logs/investigate_phase3_golden_regen_scope.md`) ยืนยันด้วย Python
จริงตอนนี้ว่า `calculate_exit_state(elements[11])` และ
`calculate_point_on_element(elements[12], 0.0)` ให้ค่าตรงกันบิตต่อบิต
(`2.164249522383976 rad` ทั้งคู่, N/E ก็ตรงกันบิตต่อบิตเช่นกัน:
`1566896.3356117962, 679737.3456812622`) — ยืนยันว่า chain นี้ไม่มี gap จริง
`get_element_index` (Python) resolve สถานีขอบนี้ไปที่ element 11 (ตัวก่อนหน้า,
ใช้ d=L) ตรงกับพฤติกรรมที่คาดไว้ของ `SMT_SolveForward` เวอร์ชันใหม่ (เลือกแถวแรก
ที่ match ด้วย tolerance) ตามที่วิเคราะห์ไว้ในหัวข้อสาม ข้อ 2

| Test | sta | Expected `SMT_WCBatSta`° | Source |
|---|---|---|---|
| Boundary (SPIN-COSINE→C junction, R=500/L=70 group) | 2249.2500679098625 | 124.00236344580601 | `test_data/SettingOutTest.csv` via `build_alignment_from_pi`; `calculate_exit_state(el[11])` == `calculate_point_on_element(el[12],0)` bit-identical |

หมายเหตุ: จุดนี้ต้องใช้ตาราง `SMT_Elements` แบบหลายแถวจริง (สร้างจาก
`elements_output.csv` หรือเทียบเท่า) ไม่ใช่แถวเดียวสังเคราะห์แบบจุดทดสอบอื่น
เพราะจุดประสงค์คือทดสอบพฤติกรรมการเลือกแถวที่ต่อกันพอดี ซึ่งตารางแถวเดียวทดสอบ
ไม่ได้

---

## แปด — ตรวจสอบฝั่ง Python ว่ามีสูตรแยกซ้ำแบบเดียวกันหรือไม่ (ตามที่ผู้ใช้ขอเพิ่ม)

grep `azimuth|theta|turning|wcb` ทั่ว `src/smt/alignment.py` และ
`src/smt/builders/alignment_builder.py`:

**ยืนยันแล้ว: ไม่มีจุดใดในทั้งสองไฟล์ที่เขียนสูตรมุม/theta แยกเองนอกเหนือจากผ่าน
`calculate_point_on_element`/`calculate_exit_state`** ทุกจุดที่คำนวณ azimuth ใน
`alignment.py` (ฟังก์ชัน `calculate_point_on_element` เอง, `calculate_exit_state`,
`calculate_station_to_coordinate`, `calculate_projection_to_element`) ล้วนเรียก
หรือ*เป็น*ฟังก์ชันแกนเดียวกันนี้ ไม่มี re-implementation ของสูตรมุมที่ไหนอีก

จุดเดียวที่น่าสนใจและใกล้เคียงกับรูปแบบปัญหานี้ที่สุดคือ
`alignment_builder.py::_spiral_turning_angle` (บรรทัด 139-150):
```python
def _spiral_turning_angle(R: float, length: float, trans: str | None) -> float:
    """Real accumulated turning angle (radians) of one spiral, R/length/shape only.
    Built via a synthetic SPIN element at the origin (k_in=0, k_out=1/R, entry azimuth
    ...
    """
    ...
    return calculate_exit_state(el).azimuth - el.azimuth
```
ฟังก์ชันนี้**ไม่ใช่สูตรแยก** — มันสร้าง synthetic Element แล้วเรียก
`calculate_exit_state` (ซึ่งเรียก `calculate_point_on_element` ภายใน) จริง แค่ลบ
entry azimuth ออกเพื่อได้ theta อย่างเดียว เป็น wrapper บาง ๆ รอบ engine เดียวกัน
ไม่ใช่ re-implementation — **ปลอดภัย ไม่ใช่บั๊กแบบเดียวกับ `SMT_WCBatSta` เดิม**

มีคอมเมนต์เก่าที่น่าสนใจที่บรรทัด 100: `# assumes theta=Ls/(2R); real turning
angle needed for the COSINE closed form.` — นี่คือคอมเมนต์อธิบายบั๊กเดิมที่*เคย*มี
ใน `_build_curve_sub_elements` (แก้ไปแล้วตาม
`session_logs/investigate_build_curve_sub_elements_fix.md`, ดู CLAUDE.md Known
limits) ไม่ใช่บั๊กที่ยังเหลืออยู่ตอนนี้ — คอมเมนต์นี้อธิบายประวัติ ไม่ใช่ TODO

**สรุปข้อแปด**: ฝั่ง Python ไม่มีจุดที่ต้องแก้เพิ่ม ยืนยันว่า `SMT_WCBatSta` เดิมเป็น
บั๊กเฉพาะฝั่ง VBA เท่านั้น (จุดเดียวที่หลุดออกจากวินัย "single source of truth" ที่
Python ทั้งไฟล์ยึดถืออยู่แล้ว)

---

## สรุปขอบเขตงาน

แก้ 2 ฟังก์ชันใน `reference/vba/SMT_Alignment.bas` เท่านั้น:
1. `SMT_SolveForward` — ขยาย return array เป็น 3 element (เพิ่ม tangent azimuth)
2. `SMT_WCBatSta` — เขียนใหม่ทั้งฟังก์ชันให้ delegate ผ่าน `SMT_SolveForward`
   แทนสูตรมุมเอง

ไม่กระทบไฟล์ VBA อื่น ไม่กระทบ Python (ยืนยันแล้วในหัวข้อแปด) ยังไม่แก้ไฟล์ใดๆ ใน
รอบนี้ รอ apply หลังอนุมัติ
