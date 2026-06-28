# SMT CLI — คู่มือการใช้งาน Command-Line Interface

**Surveyor Micro Toolkit (SMT)** เวอร์ชัน 0.1.0  
เครื่องมือคำนวณงานแนวเส้นทางถนน/สะพาน/ทางลาด ผ่าน Command Line

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

**ลำดับการใช้งานทั่วไป:**
```
SettingOutTest.csv (PI table)
        ↓
   smt build          → elements_output.csv + controls_so_output.csv
        ↓
   smt station-to-coord / smt coord-to-station   (ใช้ elements_output.csv)
        ↓
   smt cross-check    (ใช้ PI table + field data)
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
| `pi_table.csv` | ✅ | ไฟล์ PI table (รูปแบบด้านล่าง) |
| `--out-dir DIR` | ❌ | โฟลเดอร์สำหรับ output (default: โฟลเดอร์เดียวกับ input) |

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

**คำอธิบายแต่ละคอลัมน์:**

| คอลัมน์ | คำอธิบาย | หมายเหตุ |
|---------|---------|---------|
| POINT | ชื่อจุด: BP, PI1..PIx, EP | แถวว่าง = compound sub-arc |
| STA | station เริ่มต้น (BP เท่านั้น) | PIอื่นๆ ว่างได้ (คำนวณอัตโนมัติ) |
| NORTHING | พิกัด N (เหนือ) | |
| EASTING | พิกัด E (ตะวันออก) | |
| RADIUS | รัศมีโค้ง (เมตร) | 0 หรือว่าง = angle point (ไม่มีโค้ง) |
| Ls | ความยาว spiral สมมาตร | |
| LsIn | ความยาว spiral เข้า (อสมมาตร) | |
| LsOut | ความยาว spiral ออก (อสมมาตร) | |
| Transition | ชนิด transition: CLOTHOID, BLOSS, COSINE, SINE | ว่าง = CLOTHOID |
| Delta | มุมเลี้ยวของ arc ใน compound curve (องศา) | ใช้กับแถว compound sub-arc |

**รูปแบบพิเศษ:**
- **Compound curve:** PI row ตามด้วยแถวที่ POINT ว่าง แต่มี RADIUS และ DELTA เช่น PI7 (R=300, Delta=20°) ตามด้วย แถวว่าง (R=150)
- **Angle point (EXT-001):** RADIUS=0 หรือว่าง → ไม่มีโค้ง สร้าง control point ชื่อ IP

### output ที่ได้

**`elements_output.csv`** — ตาราง element สำหรับใช้กับ smt station-to-coord และ smt coord-to-station
```
StaStart,StaEnd,N,E,Azimuth,Radius,Type,Transition
0.000,519.615,1568000.000,678000.000,90.000000,0.000,T,CLOTHOID
519.615,676.695,1568000.000,678519.615,90.000000,300.000,C,CLOTHOID
676.695,1020.591,1567959.808,678669.615,120.000012,0.000,T,CLOTHOID
...
```

| คอลัมน์ | คำอธิบาย |
|---------|---------|
| StaStart | station เริ่มต้นของ element (เมตร) |
| StaEnd | station สิ้นสุดของ element (เมตร) |
| N | พิกัด N ที่จุดเริ่มต้น element |
| E | พิกัด E ที่จุดเริ่มต้น element |
| Azimuth | มุมแนว entry tangent (องศา, survey convention) |
| Radius | รัศมี + = ขวา, − = ซ้าย, 0 = เส้นตรง |
| Type | T (tangent), C (circular), SPIN (spiral เข้า), SPOUT (spiral ออก) |
| Transition | CLOTHOID, BLOSS, COSINE, SINE |

**`controls_so_output.csv`** — จุดควบคุมทั้งหมด สำหรับ setting out และ checking
```
Name,STA,N,E
BP,0.000,1568000.000,678000.000
PC,519.615,1568000.000,678519.615
PT,676.695,1567959.808,678669.615
TS,1020.591,1567787.860,678967.438
SC,1080.591,1567756.578,679018.621
CS,1299.844,1567590.715,679157.796
ST,1359.844,1567534.878,679179.714
IP,5890.784,1565380.681,680198.141
EP,7070.151,1565724.112,679180.443
```

| ชื่อจุด | ความหมาย |
|--------|---------|
| BP | Beginning Point (จุดเริ่มต้น) |
| EP | End Point (จุดสิ้นสุด) |
| PC | Point of Curvature (เริ่มโค้ง) |
| PT | Point of Tangency (สิ้นสุดโค้ง) |
| TS | Tangent to Spiral |
| SC | Spiral to Curve |
| CS | Curve to Spiral |
| ST | Spiral to Tangent |
| PCC | Point of Compound Curve |
| IP | Intersection Point (angle point ไม่มีโค้ง) |

### ตัวอย่างการใช้งาน

```powershell
# สร้าง output ในโฟลเดอร์เดียวกับ input
smt build test_data\SettingOutTest.csv

# กำหนดโฟลเดอร์ output เอง
smt build test_data\SettingOutTest.csv --out-dir output\

# ตัวอย่างผลลัพธ์ใน terminal
=== Elements (31 rows) -> output\elements_output.csv ===
  StaStart     StaEnd            N            E      Az(deg)     Radius Type   Trans
------------------------------------------------------------------------------------------
     0.000    519.615  1568000.000   678000.000   90.000000      0.000 T      CLOTHOID
   519.615    676.695  1568000.000   678519.615   90.000000    300.000 C      CLOTHOID
...

=== Control Points (32 rows) -> output\controls_so_output.csv ===
Name              STA              N              E
--------------------------------------------------
BP            0.000  1568000.000   678000.000
PC          519.615  1568000.000   678519.615
...
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
| `elements.csv` | ✅ | ไฟล์ element table (จาก smt build) |
| `sta` | ✅ | station ที่ต้องการหาพิกัด (เมตร) |
| `--offset OFFSET` | ❌ | offset จากแนวกลาง (เมตร, + = ขวา, − = ซ้าย, default = 0) |

### output
```
N,E
```
(พิกัด N และ E คั่นด้วย comma)

### ตัวอย่างการใช้งาน
```powershell
# หาพิกัด centerline ที่ sta=500
smt station-to-coord test_data\build_out\elements_output.csv 500
# output: 1568000.000,678500.000

# หาพิกัดที่ sta=500 offset +5m (ขวา)
smt station-to-coord test_data\build_out\elements_output.csv 500 --offset 5
# output: 1567995.000,678500.000

# หาพิกัดที่ sta=1000 offset -10m (ซ้าย)
smt station-to-coord test_data\build_out\elements_output.csv 1000 --offset -10
```

---

## 3. smt coord-to-station — หา Station จากพิกัด

### รูปแบบคำสั่ง
```
smt coord-to-station <elements.csv> <n> <e>
```

### arguments
| argument | จำเป็น | คำอธิบาย |
|----------|--------|---------|
| `elements.csv` | ✅ | ไฟล์ element table (จาก smt build) |
| `n` | ✅ | พิกัด N (เหนือ) |
| `e` | ✅ | พิกัด E (ตะวันออก) |

### output
```
sta,offset
```
(station และ offset คั่นด้วย comma)  
offset + = ขวา, − = ซ้าย

### ตัวอย่างการใช้งาน
```powershell
# หา station ของพิกัดที่รู้
smt coord-to-station test_data\build_out\elements_output.csv 1568000 678500
# output: 500.000,0.000

# หา station ของจุดที่อยู่ขวาแนว 5m
smt coord-to-station test_data\build_out\elements_output.csv 1567995 678500
# output: 500.000,5.000
```

---

## 4. smt cross-check — ตรวจสอบจุดสนามกับแนวเส้นทาง

### รูปแบบคำสั่ง
```
smt cross-check <pi_table.csv> <field.csv>
```

### arguments
| argument | จำเป็น | คำอธิบาย |
|----------|--------|---------|
| `pi_table.csv` | ✅ | ไฟล์ PI table (รูปแบบเดียวกับ smt build) |
| `field.csv` | ✅ | ไฟล์ข้อมูลสนาม |

### รูปแบบ input: field CSV
```
POINT,N,E,Z,DISC
1001,1568047.495,678073.812,101.255,EG
1002,1567980.056,678584.785,101.253,EG
1003,1567715.803,679156.230,101.250,EG
```

| คอลัมน์ | คำอธิบาย |
|---------|---------|
| POINT | ชื่อหรือหมายเลขจุด |
| N | พิกัด N ที่วัดได้ในสนาม |
| E | พิกัด E ที่วัดได้ในสนาม |
| Z | ความสูง (elevation) |
| DISC | คำอธิบาย เช่น EG (Existing Ground) |

### output
```
NAME              STA     OFFSET            N            E         Z     DISC
-----------------------------------------------------------------------------
1001           73.812    -47.495  1568047.495   678073.812   101.255       EG
1002          588.205     12.461  1567980.056   678584.785   101.253       EG
...
```

| คอลัมน์ | คำอธิบาย |
|---------|---------|
| NAME | ชื่อจุดจาก field CSV |
| STA | station บนแนวกลาง (เมตร) |
| OFFSET | ระยะห่างจากแนวกลาง (+ = ขวา, − = ซ้าย, เมตร) |
| N, E | พิกัดจากสนาม |
| Z | ความสูงจากสนาม |
| DISC | คำอธิบาย |

### ตัวอย่างการใช้งาน
```powershell
smt cross-check test_data\SettingOutTest.csv test_data\Bulk_cross-check.csv
```

---

## การจัดการ Error

| Error message | สาเหตุ | วิธีแก้ |
|--------------|--------|--------|
| `error: could not convert string to float: 'BP'` | ใช้ PI table กับคำสั่งที่ต้องการ elements table | ใช้ `smt build` สร้าง elements_output.csv ก่อน |
| `error: [Errno 2] No such file or directory` | ไม่พบไฟล์ | ตรวจ path ให้ถูกต้อง |
| `error: station ... lies outside the alignment` | station อยู่นอกช่วง alignment | ตรวจ station ให้อยู่ในช่วง StaStart ถึง StaEnd |
| `warning: PI#x: spiral ยาวเกินมุมเลี้ยว` | spiral ยาวเกินไปสำหรับมุมเลี้ยว | ลด Ls หรือเพิ่ม R ใน PI table |

---

## Workflow ตัวอย่างงานจริง

### งาน Setting Out
```powershell
# ขั้น 1: สร้างตารางแนวเส้นทาง
smt build SettingOutTest.csv --out-dir output\

# ขั้น 2: หาพิกัดจุดต่างๆ ตาม station
smt station-to-coord output\elements_output.csv 1000
smt station-to-coord output\elements_output.csv 1000 --offset 3.5
smt station-to-coord output\elements_output.csv 1000 --offset -3.5
```

### งาน Cross-Section Survey
```powershell
# ขั้น 1: หา station ของจุดที่วัดมา
smt coord-to-station output\elements_output.csv 1567787 678967
```

### งาน Bulk Field Check
```powershell
# ขั้น 1: ตรวจสอบทุกจุดพร้อมกัน
smt cross-check SettingOutTest.csv field_survey.csv
```

---

## หมายเหตุสำคัญ

**Sign Convention:**
- Offset + = ขวาของทิศทางเดินทาง
- Offset − = ซ้ายของทิศทางเดินทาง
- Radius + = โค้งขวา
- Radius − = โค้งซ้าย

**หน่วย:**
- ระยะทางทั้งหมด: เมตร
- มุม Azimuth ใน elements.csv: องศา (survey convention, 0° = เหนือ, วนตามเข็มนาฬิกา)
- การคำนวณภายใน: radian (แปลงเป็นองศาที่ output เท่านั้น)

**Angle Point (EXT-001):**
- PI ที่ RADIUS = 0 หรือว่าง → ไม่สร้างโค้ง สร้าง control point ชื่อ **IP**
- ใช้ได้กับ PI ที่ collinear (อยู่ในแนวเดียวกัน) ด้วย
