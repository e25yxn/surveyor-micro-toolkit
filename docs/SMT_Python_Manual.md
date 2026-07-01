# SMT Python — คู่มือคำสั่งทั้งหมด

**Surveyor Micro Toolkit (SMT)** — คู่มือรวม CLI commands ทั้งหมด 7 คำสั่ง
สำหรับใช้เป็น reference ประจำตัว | อัปเดตล่าสุด: กรกฎาคม 2026

---

## การเปิดใช้งาน (ทำทุกครั้งที่เปิด terminal ใหม่)

```powershell
cd "D:\My Second Project\SurveyorMicroToolkit"
.\.venv\Scripts\Activate.ps1
```

ตรวจสอบว่าพร้อมใช้งาน:

```powershell
smt --help
```

---

## ภาพรวมคำสั่งทั้งหมด

| # | คำสั่ง | Input | Output | ใช้เมื่อ |
|---|--------|-------|--------|---------|
| 1 | `smt build` | PI table CSV | elements CSV + controls CSV | สร้างตารางแนวเส้นทางจาก PI |
| 2 | `smt station-to-coord` | elements CSV + station | N, E | หาพิกัดจาก station |
| 3 | `smt coord-to-station` | elements CSV + N, E | station, offset | หา station จากพิกัด |
| 4 | `smt cross-check` | PI table CSV + field CSV | ตารางผล | ตรวจสอบจุดสนามกับแนวเส้นทาง |
| 5 | `smt compare-drawing` | elements CSV + drawing CSV | ตารางเปรียบเทียบ | ตรวจสอบความตรงกับแบบ |
| 6 | `smt fit-radius` | PI table CSV + drawing CSV | R ที่ปรับแล้ว | ปรับ R ให้ตรงกับแบบมากที่สุด |
| 7 | `smt export-landxml` | PI table CSV | LandXML 1.2 (.xml) | ส่งออกไป Civil 3D 2023 |

### Workflow มาตรฐานของงานจริง

```
PI table CSV (SettingOutTest.csv)
        │
        ▼
   smt build ─────────► elements_output.csv + controls_so_output.csv
        │                          │
        ▼                          ▼
   smt fit-radius            smt station-to-coord
   (ถ้า gap ใหญ่)             smt coord-to-station
        │                          │
        ▼                          ▼
   smt compare-drawing ◄───── เปรียบเทียบกับแบบ
        │
        ▼
   smt export-landxml ──────► ส่งเข้า Civil 3D 2023
        │
   smt cross-check ◄───────── ตรวจสอบจุดสนามจริง
```

---

## 1. `smt build` — สร้างตารางแนวเส้นทางจาก PI

### รูปแบบคำสั่ง
```powershell
smt build <pi_table.csv> [--out-dir DIR]
```

### Arguments
| argument | จำเป็น | คำอธิบาย |
|----------|--------|---------|
| `pi_table.csv` | ✅ | ไฟล์ PI table |
| `--out-dir DIR` | ❌ | โฟลเดอร์ output (default: โฟลเดอร์เดียวกับ input) |

### รูปแบบ Input: PI table CSV
```
POINT,STA,NORTHING,EASTING,RADIUS,Ls,LsIn,LsOut,Transition,Delta
BP,0,1568000,678000,,,,,,
PI1,,1568000,678600,300,,,,,
PI2,,1567700,679119.615,400,60,,,,
PI3,,1567136.184,679324.827,400,60,,,BLOSS,
PI10,,1565380.681,680198.141,0,,,,,
EP,,1565724.112,679180.443,,,,,,
```

| คอลัมน์ | คำอธิบาย | หมายเหตุ |
|---------|---------|---------|
| POINT | BP, PI1..PIx, EP | แถวว่าง = compound sub-arc |
| STA | station เริ่มต้น | ใส่เฉพาะ BP |
| NORTHING / EASTING | พิกัด N, E | |
| RADIUS | รัศมีโค้ง (เมตร) | 0 หรือว่าง = angle point (ไม่มีโค้ง) |
| Ls | ความยาว spiral สมมาตร | |
| LsIn / LsOut | ความยาว spiral เข้า/ออก (อสมมาตร) | |
| Transition | CLOTHOID, BLOSS, COSINE, SINE | ว่าง = CLOTHOID |
| Delta | มุมเลี้ยว compound sub-arc | |

### Output: `elements_output.csv` (ทศนิยม 6 ตำแหน่ง)
```
StaStart,StaEnd,N,E,Azimuth,Radius,Type,Transition
0.000000,519.615000,1568000.000000,678000.000000,90.000000,0.000000,T,
519.615000,676.695000,1568000.000000,678519.615000,90.000000,300.000000,C,
```
- **Type:** T=tangent, C=circular, SPIN=spiral เข้า, SPOUT=spiral ออก
- **Radius:** + = ขวา, − = ซ้าย, 0 = tangent

### Output: `controls_so_output.csv`
```
Name,STA,N,E
BP,0.000000,1568000.000000,678000.000000
PC,519.615000,1568000.000000,678519.615000
IP,5890.784000,1565380.681000,680198.141000
```
| ชื่อจุด | ความหมาย |
|--------|---------|
| BP/EP | จุดเริ่ม/สิ้นสุด |
| PC/PT | เริ่ม/สิ้นสุดโค้ง |
| TS/SC/CS/ST | จุด spiral |
| PCC | Compound curve |
| IP | Angle point (ไม่มีโค้ง) |

### ตัวอย่าง
```powershell
smt build test_data\SettingOutTest.csv --out-dir output\
smt build D:\Pnez_data\ramp01n01_SO.csv --out-dir D:\Pnez_data\output\
```

---

## 2. `smt station-to-coord` — หาพิกัดจาก Station

### รูปแบบคำสั่ง
```powershell
smt station-to-coord <elements.csv> <sta> [--offset OFFSET]
```

| argument | จำเป็น | คำอธิบาย |
|----------|--------|---------|
| `elements.csv` | ✅ | ไฟล์จาก `smt build` |
| `sta` | ✅ | station (เมตร) |
| `--offset` | ❌ | + = ขวา, − = ซ้าย (default 0) |

### ตัวอย่าง
```powershell
smt station-to-coord output\elements_output.csv 500
# 1568000.000000,678500.000000

smt station-to-coord output\elements_output.csv 500 --offset 5
smt station-to-coord output\elements_output.csv 1000 --offset -10
```

---

## 3. `smt coord-to-station` — หา Station จากพิกัด

### รูปแบบคำสั่ง
```powershell
smt coord-to-station <elements.csv> <n> <e>
```

### ตัวอย่าง
```powershell
smt coord-to-station output\elements_output.csv 1568000 678500
# 500.000000,0.000000
```

---

## 4. `smt cross-check` — ตรวจสอบจุดสนามกับแนวเส้นทาง

### รูปแบบคำสั่ง
```powershell
smt cross-check <pi_table.csv> <field.csv>
```

### รูปแบบ field CSV
```
POINT,N,E,Z,DISC
1001,1568047.495,678073.812,101.255,EG
```

### Output
```
NAME              STA     OFFSET            N            E         Z     DISC
-----------------------------------------------------------------------------
1001           73.812    -47.495  1568047.495   678073.812   101.255       EG
```

### ตัวอย่าง
```powershell
smt cross-check test_data\SettingOutTest.csv test_data\Bulk_cross-check.csv
```

---

## 5. `smt compare-drawing` — ตรวจสอบความตรงกับแบบ

### รูปแบบคำสั่ง
```powershell
smt compare-drawing <elements.csv> <drawing.csv> [--tol TOLERANCE]
```

| argument | จำเป็น | คำอธิบาย |
|----------|--------|---------|
| `elements.csv` | ✅ | จาก `smt build` |
| `drawing.csv` | ✅ | พิกัดจากแบบ (Name, STA, N, E) |
| `--tol` | ❌ | tolerance เมตร (default 0.010) |

### รูปแบบ drawing CSV
```
Name,STA,N,E
BP,0,1537796.012,685410.478
PI,27.23,1537790.869,685383.738
PC,53.874,1537776.655,685360.512
```
> จุดที่ชื่อขึ้นต้น PI/HIP = intersection point ไม่ได้อยู่บน centerline → แสดงเป็น HIP

### Output
```
NAME  STA          N_DRAW        E_DRAW        N_CALC        E_CALC        DELTA_N   DELTA_E   GAP_M    OK
BP    0.000000     1537796.012   685410.478    1537796.012   685410.478    0.000000  0.000000  0.000000  OK
PI    27.230000    1537790.869   685383.738    -             -             -         -         -         HIP
```

### ตัวอย่าง
```powershell
smt compare-drawing test_data\r01n01_elements_output.csv test_data\r01n01_so_crosscheck.csv
smt compare-drawing output\elements_output.csv drawing.csv --tol 0.005
```

---

## 6. `smt fit-radius` — ปรับ R ให้ตรงกับแบบมากที่สุด (Optimizer)

ใช้ scipy Nelder-Mead หาค่า R ที่ทำให้ gap รวมน้อยที่สุด โดยรักษา sign (ทิศทางเลี้ยว) ไว้เสมอ

### การติดตั้ง (ครั้งแรกเท่านั้น)
```powershell
pip install "surveyor-micro-toolkit[optimize]"
```

### รูปแบบคำสั่ง
```powershell
smt fit-radius <pi_table.csv> <drawing.csv> [--fix PI1,PI2] [--tol 1e-6] [--max-iter 10000]
```

| argument | จำเป็น | คำอธิบาย |
|----------|--------|---------|
| `pi_table.csv` | ✅ | PI table เดิม |
| `drawing.csv` | ✅ | พิกัดจากแบบ |
| `--fix` | ❌ | ชื่อ PI ที่ไม่ต้องการปรับ (comma-separated) |
| `--tol` | ❌ | ความละเอียด (default 1e-6) |
| `--max-iter` | ❌ | จำนวนรอบสูงสุด (default 10000) |

### Output ตัวอย่างจริง
```
=== fit-radius: 5 free PI(s), 9 drawing point(s) ===
PI                R_initial    R_optimized
------------------------------------------
PI1             -150.000000    -149.905419
PI2              150.000000     150.071084
gap_before: 0.014717 m
gap_after:  0.001206 m
iterations: 289  converged: True

=== Verification (gap after optimisation) ===
Name                STA         calc_N         calc_E      gap_m
BP             0.000000 1537796.012000  685410.478000   0.000000
```

### ตัวอย่าง
```powershell
smt fit-radius test_data\ramp01n01_SO.csv test_data\r01n01_so_crosscheck.csv
smt fit-radius test_data\SO.csv test_data\drawing.csv --fix PI1,PI5 --tol 1e-8
```

### หมายเหตุสำคัญ
- IP (angle point, R=0) จะถูก skip อัตโนมัติ ไม่ optimize
- ถ้า gap ก่อน optimize < 10mm → มักเป็น rounding error ในแบบ ไม่ใช่ design ผิด
- ถ้า ΔR ที่ได้ < 1m บน R หลักร้อยเมตร → แบบยัง valid ใช้ R เดิม (กลมๆ) ได้

---

## 7. `smt export-landxml` — ส่งออก LandXML สำหรับ Civil 3D 2023

### รูปแบบคำสั่ง
```powershell
smt export-landxml <pi_table.csv> [--name NAME] [--out FILE.xml]
```

| argument | จำเป็น | คำอธิบาย |
|----------|--------|---------|
| `pi_table.csv` | ✅ | PI table |
| `--name` | ❌ | ชื่อ alignment ใน XML (default: alignment) |
| `--out` | ❌ | path ไฟล์ output (ไม่ใส่ = แสดงหน้าจอ) |

### ตัวอย่าง
```powershell
# แสดงผลหน้าจอ
smt export-landxml test_data\SettingOutTest.csv --name SettingOutTest

# บันทึกเป็นไฟล์
smt export-landxml test_data\SettingOutTest.csv --name SettingOutTest --out test_data\SettingOutTest.xml
```

### การ Import เข้า Civil 3D 2023
1. เปิด Civil 3D → **Insert → LandXML**
2. เลือกไฟล์ `.xml` ที่ export มา
3. Alignment จะปรากฏใน Prospector พร้อม PC/PT/spiral ครบ

### Mapping ชนิด Spiral (SMT → Civil 3D)
| SMT Transition | Civil 3D spiType |
|---|---|
| CLOTHOID | clothoid |
| BLOSS | bloss |
| SINE | sinusoid |
| COSINE | sineHalfWave |

### ข้อควรระวัง
- Coordinate order ใน LandXML คือ **N E** (Northing ก่อน Easting) ตามมาตรฐาน Civil 3D
- `rot` ใช้ค่า `"cw"`/`"ccw"` เท่านั้น (ไม่ใช่ right/left)
- Spiral มี attribute พิเศษ `theta`, `totalX`, `totalY`, `tanLong`, `tanShort` ที่ Civil 3D ต้องการเพื่อวางตำแหน่งถูกต้อง

---

## การจัดการ Error ที่พบบ่อย

| Error message | สาเหตุ | วิธีแก้ |
|--------------|--------|--------|
| `could not convert string to float: 'BP'` | ใช้ PI table กับคำสั่งที่ต้องการ elements table | รัน `smt build` ก่อน |
| `ไม่พบข้อมูล PI ในไฟล์` | ใช้ elements table กับ `smt build` | ตรวจว่าไฟล์มีคอลัมน์ POINT |
| `station ... lies outside the alignment` | station นอกช่วง | ตรวจ StaStart–StaEnd |
| `PI#x: spiral ยาวเกินมุมเลี้ยว` | Ls ยาวเกินไป | ลด Ls หรือเพิ่ม R |
| `ModuleNotFoundError: scipy` | ยังไม่ติดตั้ง optimize extras | `pip install "surveyor-micro-toolkit[optimize]"` |

---

## Sign Convention (ใช้เหมือนกันทุกคำสั่ง)

| ปริมาณ | + | − |
|--------|---|---|
| Offset | ขวาของทิศทางเดินทาง | ซ้ายของทิศทางเดินทาง |
| Radius | โค้งขวา | โค้งซ้าย |
| Azimuth | 0–360° วัดตามเข็มจากทิศเหนือ | (normalize เสมอ) |

**หน่วย:** ระยะทั้งหมดเป็นเมตร ยกเว้น Azimuth เป็นองศา
**ความแม่นยำ:** output ทศนิยม 6 ตำแหน่งเสมอ (ไม่ปัดกลางทาง)

---

## Workflow ตัวอย่างงานจริงแบบครบวงจร

```powershell
# ขั้น 1 — สร้างตารางแนวเส้นทาง
smt build test_data\SettingOutTest.csv --out-dir output\

# ขั้น 2 — ตรวจสอบกับแบบ
smt compare-drawing output\elements_output.csv drawing.csv

# ขั้น 3 — ถ้า gap ใหญ่เกินไป ปรับ R
smt fit-radius test_data\SettingOutTest.csv drawing.csv

# ขั้น 4 — หาพิกัดจาก station เพื่อ setting out
smt station-to-coord output\elements_output.csv 500 --offset 3.5

# ขั้น 5 — ตรวจสอบจุดที่วัดจากสนามจริง
smt cross-check test_data\SettingOutTest.csv field_survey.csv

# ขั้น 6 — ส่งออกไป Civil 3D
smt export-landxml test_data\SettingOutTest.csv --name MyRoad --out output\MyRoad.xml
```

---

## คำสั่งเสริม — ตรวจสอบระบบก่อนเริ่มงาน

```powershell
# ตรวจว่า environment พร้อม
pytest -q                    # ต้องได้ 438/438 passed
git status                   # ตรวจว่าไม่มีไฟล์ค้าง
smt --help                   # แสดงคำสั่งทั้งหมด
```
