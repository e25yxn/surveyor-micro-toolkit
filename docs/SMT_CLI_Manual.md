# SMT CLI — คู่มือการใช้งาน Command-Line Interface

**Surveyor Micro Toolkit (SMT)** เวอร์ชัน 0.1.0  
เครื่องมือคำนวณงานแนวเส้นทางถนน/สะพาน/ทางลาด ผ่าน Command Line  
396/396 tests ผ่าน — mypy 0 errors

---

## การติดตั้ง

```powershell
cd "D:\My Second Project\SurveyorMicroToolkit"
.\.venv\Scripts\Activate.ps1
pip install -e .
```

ตรวจสอบว่าติดตั้งสำเร็จ:
```powershell
smt --help
```

---

## ภาพรวม subcommands ทั้งหมด

| คำสั่ง | input | output | ใช้เมื่อ |
|--------|-------|--------|---------|
| `smt build` | PI table CSV | elements CSV + controls CSV | สร้างตารางแนวเส้นทางจาก PI |
| `smt station-to-coord` | elements CSV + station | N, E | หาพิกัดจาก station |
| `smt coord-to-station` | elements CSV + N, E | station, offset | หา station จากพิกัด |
| `smt cross-check` | PI table CSV + field CSV | ตารางผล | ตรวจสอบจุดสนามกับแนวเส้นทาง |
| `smt compare-drawing` | elements CSV + drawing CSV | ตารางเปรียบเทียบ | ตรวจสอบความตรงกับแบบ |

**Workflow งานจริง:**
```
PI table CSV (SettingOutTest.csv)
        ↓
   smt build          → elements_output.csv + controls_so_output.csv
        ↓                       ↓
   smt station-to-coord    smt compare-drawing  ← เปรียบเทียบกับแบบ
   smt coord-to-station
        ↓
   smt cross-check    ← ตรวจสอบจุดสนาม
```

---

## 1. smt build — สร้างตารางแนวเส้นทางจาก PI

### รูปแบบคำสั่ง
```
smt build <pi_table.csv> [--out-dir DIR]
```

### arguments
| argument | จำเป็น | คำอธิบาย |
|----------|--------|---------|
| `pi_table.csv` | ✅ | ไฟล์ PI table |
| `--out-dir DIR` | ❌ | โฟลเดอร์ output (default: โฟลเดอร์เดียวกับ input) |

### รูปแบบ input: PI table CSV
```
POINT,STA,NORTHING,EASTING,RADIUS,Ls,LsIn,LsOut,Transition,Delta
BP,0,1568000,678000,,,,,,
PI1,,1568000,678600,300,,,,,
PI2,,1567700,679119.615,400,60,,,,
PI3,,1567136.184,679324.827,400,60,,,BLOSS,
PI6,,1565942.4,680704.231,400,,50,90,,
PI7,,1565169.659,680911.287,300,,,,,20
,,,,150,,,,,
PI10,,1565380.681,680198.141,0,,,,,
EP,,1565724.112,679180.443,,,,,,
```

**คำอธิบายคอลัมน์:**

| คอลัมน์ | คำอธิบาย | หมายเหตุ |
|---------|---------|---------|
| POINT | ชื่อจุด: BP, PI1..PIx, EP | แถวว่าง = compound sub-arc |
| STA | station เริ่มต้น (BP เท่านั้น) | PIอื่นๆ ว่างได้ (คำนวณอัตโนมัติ) |
| NORTHING | พิกัด N (เหนือ) | |
| EASTING | พิกัด E (ตะวันออก) | |
| RADIUS | รัศมีโค้ง (เมตร) | 0 หรือว่าง = angle point (EXT-001) |
| Ls | ความยาว spiral สมมาตร | |
| LsIn | ความยาว spiral เข้า (อสมมาตร) | |
| LsOut | ความยาว spiral ออก (อสมมาตร) | |
| Transition | CLOTHOID, BLOSS, COSINE, SINE | ว่าง = CLOTHOID |
| Delta | มุมเลี้ยวของ arc ใน compound curve (องศา) | ใช้กับแถว compound sub-arc |

**รูปแบบพิเศษ:**
- **Compound curve:** PI row ตามด้วยแถวที่ POINT ว่างแต่มี RADIUS และ DELTA
- **Angle point (EXT-001):** RADIUS=0 หรือว่าง → ไม่มีโค้ง สร้าง control point ชื่อ IP

### output ที่ได้

**`elements_output.csv`** (ทศนิยม 6 ตำแหน่ง)
```
StaStart,StaEnd,N,E,Azimuth,Radius,Type,Transition
0.000000,519.615000,1568000.000000,678000.000000,90.000000,0.000000,T,
519.615000,676.695000,1568000.000000,678519.615000,90.000000,300.000000,C,
1080.591000,1299.844000,1567756.578000,679018.621000,120.000012,400.000000,SPIN,BLOSS
```

| คอลัมน์ | คำอธิบาย |
|---------|---------|
| Type | T=tangent, C=circular, SPIN=spiral เข้า, SPOUT=spiral ออก |
| Transition | แสดงเฉพาะ SPIN/SPOUT (T/C ว่าง) |
| Radius | + = ขวา, − = ซ้าย, 0 = tangent |

**`controls_so_output.csv`** (ทศนิยม 6 ตำแหน่ง)
```
Name,STA,N,E
BP,0.000000,1568000.000000,678000.000000
PC,519.615000,1568000.000000,678519.615000
PT,676.695000,1567959.808000,678669.615000
IP,5890.784000,1565380.681000,680198.141000
EP,7070.151000,1565724.112000,679180.443000
```

| ชื่อจุด | ความหมาย |
|--------|---------|
| BP/EP | จุดเริ่มต้น/สิ้นสุด |
| PC/PT | เริ่ม/สิ้นสุดโค้ง |
| TS/SC/CS/ST | จุด spiral |
| PCC | Compound curve |
| IP | Angle point (ไม่มีโค้ง, EXT-001) |

### ตัวอย่าง
```powershell
smt build test_data\SettingOutTest.csv --out-dir output\
smt build D:\Pnez_data\ramp01n01_SO.csv --out-dir D:\Pnez_data\output\
```

---

## 2. smt station-to-coord — หาพิกัดจาก Station

### รูปแบบคำสั่ง
```
smt station-to-coord <elements.csv> <sta> [--offset OFFSET]
```

### arguments
| argument | จำเป็น | คำอธิบาย |
|----------|--------|---------|
| `elements.csv` | ✅ | ไฟล์ elements_output.csv จาก smt build |
| `sta` | ✅ | station (เมตร) |
| `--offset` | ❌ | offset + = ขวา, − = ซ้าย (default = 0) |

### ตัวอย่าง
```powershell
smt station-to-coord output\elements_output.csv 500
# output: 1568000.000000,678500.000000

smt station-to-coord output\elements_output.csv 500 --offset 5
smt station-to-coord output\elements_output.csv 1000 --offset -10
```

---

## 3. smt coord-to-station — หา Station จากพิกัด

### รูปแบบคำสั่ง
```
smt coord-to-station <elements.csv> <n> <e>
```

### ตัวอย่าง
```powershell
smt coord-to-station output\elements_output.csv 1568000 678500
# output: 500.000000,0.000000
```

---

## 4. smt cross-check — ตรวจสอบจุดสนามกับแนวเส้นทาง

### รูปแบบคำสั่ง
```
smt cross-check <pi_table.csv> <field.csv>
```

### รูปแบบ field CSV
```
POINT,N,E,Z,DISC
1001,1568047.495,678073.812,101.255,EG
1002,1567980.056,678584.785,101.253,EG
```

### output
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

## 5. smt compare-drawing — ตรวจสอบความตรงกับแบบ

### รูปแบบคำสั่ง
```
smt compare-drawing <elements.csv> <drawing.csv> [--tol TOLERANCE]
```

### arguments
| argument | จำเป็น | คำอธิบาย |
|----------|--------|---------|
| `elements.csv` | ✅ | ไฟล์ elements_output.csv จาก smt build |
| `drawing.csv` | ✅ | ค่าพิกัดจากแบบ (Name, STA, N, E) |
| `--tol` | ❌ | tolerance (เมตร, default = 0.010) |

### รูปแบบ drawing CSV
```
Name,STA,N,E
BP,0,1537796.012,685410.478
PI,27.23,1537790.869,685383.738
PC,53.874,1537776.655,685360.512
PT,109.663,1537756.948,685308.663
EP,1762.869,1537405.577,683703.662
```

**หมายเหตุ:** จุดที่ชื่อขึ้นต้น PI หรือ HIP = intersection point ไม่ได้อยู่บน centerline แสดงเป็น HIP ในผลลัพธ์

### output
```
NAME  STA          N_DRAW         E_DRAW         N_CALC         E_CALC         DELTA_N   DELTA_E   GAP_M      OK
BP    0.000000     1537796.012000 685410.478000  1537796.012000 685410.478000  0.000000  0.000000  0.000000   OK
PI    27.230000    1537790.869000 685383.738000  -              -              -         -         -          HIP
PC    53.874000    1537776.655000 685360.512000  1537776.654521 685360.511114  0.000479  0.000886  0.001010   OK
PT    109.663000   1537756.948000 685308.663000  1537756.947753 685308.663108  0.000247  0.000108  0.000269   OK
EP    1762.869000  1537405.577000 683703.662000  1537405.576700 683703.661800  0.000300  0.000200  0.000361   OK
```

### ตัวอย่าง
```powershell
smt compare-drawing test_data\r01n01_elements_output.csv test_data\r01n01_so_crosscheck.csv
smt compare-drawing output\elements_output.csv drawing.csv --tol 0.005
```

---

## การจัดการ Error

| Error message | สาเหตุ | วิธีแก้ |
|--------------|--------|--------|
| `error: could not convert string to float: 'BP'` | ใช้ PI table กับคำสั่งที่ต้องการ elements table | รัน `smt build` สร้าง elements_output.csv ก่อน |
| `error: ไม่พบข้อมูล PI ในไฟล์` | ใช้ elements table กับ `smt build` | ตรวจว่าไฟล์มีคอลัมน์ POINT |
| `error: station ... lies outside the alignment` | station อยู่นอกช่วง alignment | ตรวจ station ให้อยู่ในช่วง StaStart ถึง StaEnd |
| `warning: PI#x: spiral ยาวเกินมุมเลี้ยว` | spiral ยาวเกินไป | ลด Ls หรือเพิ่ม R |

---

## Workflow ตัวอย่างงานจริง: ramp01n01

### ขั้น 1 — สร้างตารางแนวเส้นทาง
```powershell
smt build D:\Pnez_data\ramp01n01_SO.csv --out-dir D:\Pnez_data\output\
# ได้: elements_output.csv (12 rows) + controls_so_output.csv (13 rows)
```

### ขั้น 2 — ตรวจสอบกับแบบ
```powershell
smt compare-drawing D:\Pnez_data\output\elements_output.csv D:\Pnez_data\r01n01_so_crosscheck.csv
# max gap ≈ 0.0074m (< 1cm) — ตรงกับแบบดีมาก
```

### ขั้น 3 — หาพิกัดจาก station
```powershell
smt station-to-coord D:\Pnez_data\output\elements_output.csv 500
smt station-to-coord D:\Pnez_data\output\elements_output.csv 500 --offset 3.5
```

### ขั้น 4 — ตรวจสอบจุดสนาม
```powershell
smt cross-check D:\Pnez_data\ramp01n01_SO.csv D:\Pnez_data\field_survey.csv
```

---

## หมายเหตุสำคัญ

**Sign Convention:**
- Offset + = ขวาของทิศทางเดินทาง
- Offset − = ซ้ายของทิศทางเดินทาง
- Radius + = โค้งขวา, − = โค้งซ้าย

**หน่วย:** ทุกค่าเป็นเมตร ยกเว้น Azimuth เป็นองศา

**ความแม่นยำ:** output ทุกค่าทศนิยม 6 ตำแหน่ง

**Angle Point (EXT-001):**
RADIUS=0 หรือว่าง → ไม่มีโค้ง → control point ชื่อ IP ในแนว ramp หรือแนวที่มีจุดหักมุม
