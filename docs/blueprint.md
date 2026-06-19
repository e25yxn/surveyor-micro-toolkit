# แผนแม่บท: Python Core Engine (Master Project)
### สำหรับพัฒนาต่อใน VS Code ด้วย Claude Code — ให้เป็นองค์ความรู้กลางสำหรับต่อยอดทุกโปรเจกต์

> เอกสารนี้ทำหน้าที่ 2 อย่าง: (1) เป็น *แผน* ให้อาจารย์เดินงาน และ
> (2) เป็น *สเปก/บริบท* ให้ Claude Code อ่านเข้าใจเป้าหมาย (วางไว้เป็น `CLAUDE.md` ใน repo ได้เลย)

---

## 1. วิสัยทัศน์ — "core engine master" คืออะไร

แกนแม่บท = **ไลบรารี Python ที่บริสุทธิ์ ทดสอบครบ มีเอกสารดี** ซึ่งเป็น *แหล่งความจริงเดียว
(single source of truth)* ของคณิตศาสตร์งานแนวเส้นทาง จากแกนนี้ค่อยแตกไปเป็นอย่างอื่น
(CLI, API, Excel, เว็บ, CAD, สื่อสอน) โดย **ไม่ต้องเขียนสูตรซ้ำ**

แกนนี้ต้องเป็นได้สองสถานะพร้อมกัน:
- **เครื่องจักรที่ใช้งานจริง** (เอาไป setting-out, ตรวจแบบ, ส่งออกพิกัดได้)
- **ตำราเรียนที่อ่านรู้เรื่อง** (โค้ดสะอาด คอมเมนต์ดี มี notebook + แบบฝึก)

หลักสี่คำเดิมยังคุมทุกการตัดสินใจ: **SAFE · SMALL · STABLE · MODULAR**

---

## 2. แผนที่ความเป็นไปได้ (Landscape) — "ทุกทางที่ไปต่อได้"

จัดเป็น 5 วง จากในสุด (ต้องมั่นคงก่อน) ออกไปนอกสุด (ต่อยอด)

```
                ┌───────────────────────────────────────────────┐
                │   (5) ส่วนขยายคณิตศาสตร์อนาคต                    │
                │  ┌─────────────────────────────────────────┐  │
                │  │ (4) สื่อการสอน: notebooks, docs, viz       │  │
                │  │  ┌───────────────────────────────────┐   │  │
                │  │  │ (3) Interop: LandXML/CSV/DXF/KML    │   │  │
                │  │  │  ┌─────────────────────────────┐   │   │  │
                │  │  │  │ (2) Frontends: CLI/API/Excel │   │   │  │
                │  │  │  │   ┌───────────────────────┐ │   │   │  │
                │  │  │  │   │ (1) CORE LIBRARY      │ │   │   │  │
                │  │  │  │   │  math+alignment+      │ │   │   │  │
                │  │  │  │   │  build+cross-check    │ │   │   │  │
                │  │  │  │   └───────────────────────┘ │   │   │  │
                │  │  │  └─────────────────────────────┘   │   │  │
                │  │  └───────────────────────────────────┘   │  │
                │  └─────────────────────────────────────────┘  │
                └───────────────────────────────────────────────┘
```

### วง 1 — Core Library (ต้องมั่นคงก่อนสิ่งอื่นทั้งหมด)
คณิตศาสตร์ทั้งหมดที่เรามีอยู่แล้ว: FPMath, WCB, Alignment, Vertical, CrossFall, Surface3D,
Builders (PI→element, VPI→โค้งดิ่ง), และ **Cross-check** (เทียบค่าที่คำนวณกับค่าในแบบ)

### วง 2 — Frontends (หน้าบ้าน หลายแบบ ใช้แกนตัวเดียว)
- **CLI** (command line) — เร็วสุดที่จะมีของใช้จริง: `survey fwd --table a.csv --sta 519.6`
- **Local API** (FastAPI) — ให้โปรแกรมอื่น/เว็บเรียกผ่าน HTTP
- **Excel** ผ่าน `xlwings` (รัน Python จริงหลัง Excel — ดีกว่าพอร์ต VBA ในระยะยาว)
- **เว็บแอป / เดสก์ท็อป (PyQt, Streamlit)** — ทำทีหลังเมื่อแกนนิ่ง

### วง 3 — Interoperability (เชื่อมกับโลกสำรวจจริง — มูลค่าสูง)
- **LandXML** import/export — *มาตรฐานกลาง* ที่ Civil 3D / TBC / โปรแกรมสำรวจคุยกันได้
  (ทำให้โปรเจกต์ "ใช้ได้จริง" ไม่ใช่แค่ของเรียน)
- **CSV/TXT** จุด setting-out, **DXF** เส้นแนว/หมุด, **KML** ดูบน Google Earth

### วง 4 — Teaching Layer (สื่อการสอน — ตรงเป้าหมาย "องค์ความรู้")
- **Jupyter notebooks**: อธิบายทีละขั้น + วาดกราฟ (matplotlib) เห็นแนว/โค้ง/โปรไฟล์
- **เอกสาร** (mkdocs-material) จากบทเรียนที่เรามี + docstring
- **Visualization**: plot plan view, profile, diagram ความโค้ง — เห็นภาพช่วยเข้าใจคณิต

### วง 5 — ส่วนขยายคณิตศาสตร์อนาคต (เลือกทำเมื่อพร้อม)
- รองรับ spiral + compound (ข้อจำกัดเดิม), transition เพิ่มชนิด
- Superelevation อัตโนมัติ, งานดิน (earthwork volume), 3D corridor
- **Geodetic**: lat/long ↔ grid ผ่าน `pyproj` (UTM/Indian1975/WGS84), ปรับแก้ค่าระยะ
- **Least-squares adjustment** สำหรับงานวงรอบ/ปรับโครงข่าย

### ตารางจัดลำดับความสำคัญ
| ลำดับ | สิ่งที่ทำ | เหตุผล |
|---|---|---|
| **ฐานราก (ทำก่อน)** | วง 1 core + tests | ทุกอย่างพึ่งมัน ผิดที่นี่ผิดหมด |
| **ควรทำต่อ** | CLI + notebooks (วง 2,4) | ได้ของใช้จริง + เป็นสื่อสอนทันที |
| **คุ้มค่าสูง** | LandXML I/O (วง 3) | ปลดล็อกการใช้งานจริงกับซอฟต์แวร์อื่น |
| **ทำทีหลัง** | API, Excel/xlwings, viz เต็ม | ดีแต่รอแกนนิ่งก่อน |
| **ออปชันอนาคต** | วง 5 ทั้งหมด | ขยายเมื่อมีโจทย์จริงมารองรับ |

---

## 3. สถาปัตยกรรมที่แนะนำ (Recommended architecture)

### 3.1 โครงโฟลเดอร์ (src layout — มาตรฐานที่ดีของ Python)
```
survey-align/                  # repo root
├── pyproject.toml             # ตั้งค่า build + เครื่องมือ
├── README.md
├── CLAUDE.md                  # สเปก/บริบทให้ Claude Code (วางเอกสารนี้/ย่อไว้ตรงนี้)
├── reference/                 # ของเดิมไว้เทียบ (oracle) — สำคัญมาก
│   ├── FPMath.gs ... (engine JS ที่ผ่าน 45/45)
│   └── tables.json            # ชุดค่า golden ที่รู้คำตอบ
├── docs/
│   └── lesson.md              # บทเรียนหลักการ (ที่เราทำไว้แล้ว)
├── src/
│   └── survey_align/
│       ├── __init__.py
│       ├── fpmath.py          # มุม/ปัดเศษ/DMS
│       ├── wcb.py             # polar ↔ rectangular
│       ├── alignment.py       # Element, station_to_coord, coord_to_station ...
│       ├── vertical.py        # โค้งดิ่ง
│       ├── crossfall.py       # ยกโค้ง
│       ├── surface.py         # ผิว 3 มิติ
│       ├── builders/
│       │   ├── alignment_builder.py   # PI → element
│       │   └── vertical_builder.py    # VPI → โค้งดิ่ง
│       ├── check.py           # cross-check (เทียบค่าคำนวณ vs แบบ)
│       └── io/                # (วง 3 ทำทีหลัง) landxml.py, csv_io.py, dxf.py
├── tests/
│   ├── test_fpmath.py
│   ├── test_wcb.py
│   ├── test_alignment.py
│   ├── test_roundtrip.py      # forward→inverse = ค่าเดิม
│   └── golden/                # fixtures จาก AllTests + ค่าจาก JS oracle
├── notebooks/                 # สื่อสอน
└── examples/
```

### 3.2 จับคู่โมดูลเดิม → Python (ทำให้ Claude Code พอร์ตทีละไฟล์)
| เดิม (.gs) | ใหม่ (.py) | หน้าที่ |
|---|---|---|
| FPMath.gs | `fpmath.py` | deg/rad, normalize, angle_diff, round, DMS |
| WCB.gs | `wcb.py` | calculate_azimuth, calculate_distance_2d, calculate_forward, calculate_inverse |
| Alignment.gs | `alignment.py` | `Element` (dataclass), make_element, point_on_element, station_to_coord, project_to_element, coord_to_station, azimuth_at_station |
| Vertical.gs | `vertical.py` | level_at, grade_at |
| CrossFall.gs | `crossfall.py` | crossfall_at |
| Surface3D.gs | `surface.py` | surface_level, point_3d |
| AlignmentBuilder.gs | `builders/alignment_builder.py` | build_from_pi, cross_check |
| VerticalBuilder.gs | `builders/vertical_builder.py` | build_from_vpi |
| HorCheck/VerCheck | `check.py` | check_horizontal, check_vertical |

### 3.3 หลักการเขียนโค้ด (บังคับใช้ทั้ง repo)
- **dataclass** สำหรับ Element/State (อ่านง่าย immutable ได้ด้วย `frozen=True`)
- **type hints ทุกฟังก์ชัน** + ตรวจด้วย `mypy`
- **pure functions** ในแกน (ไม่มี I/O, ไม่มี side effect)
- **pure-Python + `math`** ก่อน (อ่านง่าย = ตำราดี) ใส่ `numpy` เฉพาะเมื่อมีเทสต์พิสูจน์ว่าจำเป็น
- เรเดียนภายใน · ปัดเศษเฉพาะตอนแสดง · เครื่องหมาย/หน่วยตามสัญญาเดิม
- docstring อธิบาย "ทำอะไร + หน่วย + เครื่องหมาย + อ้างสูตร"

### 3.4 เครื่องมือ (toolchain)
| งาน | เครื่องมือ |
|---|---|
| ทดสอบ | `pytest` (+ `hypothesis` สำหรับ property test เช่น roundtrip) |
| ตรวจชนิด | `mypy` |
| จัดรูป/ลินต์ | `ruff` (แทน black+flake8+isort ในตัวเดียว) |
| เอกสาร | `mkdocs-material` |
| แพ็กเกจ | `hatchling` ใน `pyproject.toml` |
| CI | GitHub Actions: รัน pytest + mypy + ruff ทุก push |

---

## 4. แผนเดินงานเป็นเฟส (Roadmap) — แต่ละเฟสจบเมื่อ "Definition of Done" ครบ

> หลักการ: **พอร์ตจากล่างขึ้นบน (bottom-up)** เพราะชั้นบนพึ่งชั้นล่าง และ **TDD**
> (เขียนเทสต์ค่าที่รู้คำตอบก่อน → ให้โค้ดทำให้ผ่าน)

| เฟส | งาน | Definition of Done |
|---|---|---|
| 0 | ตั้ง repo + โครงโฟลเดอร์ + toolchain + ใส่ reference (JS+tables.json) + CLAUDE.md | `pytest` รันได้ (แม้ยังว่าง), ruff/mypy ผ่าน |
| 1 | พอร์ต `fpmath` + `wcb` | เทสต์ค่ารู้คำตอบผ่าน (deg/rad, normalize, forward/inverse) |
| 2 | พอร์ต `alignment` (แกนหลัก) | golden 30-element + 31 control ผ่าน, roundtrip = 0 |
| 3 | พอร์ต `vertical` + `crossfall` + `surface` | golden โค้งดิ่ง/ยกโค้ง/ผิวผ่าน |
| 4 | พอร์ต builders (PI→element, VPI→โค้งดิ่ง) | สร้างจาก PI แล้วได้ตารางตรง JS |
| 5 | พอร์ต `check` (cross-check) | ตรวจชุดทดสอบเดิมได้ผลตรง (AllTests 45/45 เทียบเท่า) |
| 6 | CLI + notebook สอน 1 ตัว | สั่ง fwd/inv จาก command line ได้ + notebook วาด plan view |
| 7 | docs + packaging + CI | `pip install -e .` ได้, เว็บ docs ขึ้น, CI เขียว |
| 8+ | (เลือก) LandXML I/O → API → viz → วง 5 | ตามโจทย์จริง |

---

## 5. ทำงานกับ Claude Code อย่างไร (โค้ช)

### 5.1 ตั้งบริบทให้ Claude Code เข้าใจก่อน (สำคัญที่สุด)
- วาง **`CLAUDE.md`** ที่ราก repo บอก: เป้าหมาย, หลัก SAFE/SMALL/STABLE/MODULAR,
  กติกาโค้ด (pure, type hints, เรเดียนภายใน, ไม่ปัดกลางทาง, สัญญาเครื่องหมาย),
  ตารางจับคู่โมดูล, และประโยคทอง: *"engine JS ใน `reference/` คือ oracle — Python ต้องให้ค่าตรงกับมัน เทียบด้วย golden tests"*
- วาง `reference/` (JS + tables.json) ไว้จริง เพื่อให้ Claude Code เปิดอ่านเทียบได้

### 5.2 วิธีทำงาน (workflow)
1. **TDD**: บอกค่า "ที่รู้คำตอบ" ก่อน → ให้ Claude Code เขียนเทสต์ + โค้ดจนเขียว
2. **พอร์ตทีละโมดูล bottom-up** (fpmath → wcb → alignment → ...)
3. **commit เล็กๆ บ่อยๆ** + รีวิว diff ทุกครั้ง (อาจารย์คือคนตรวจค่ากับงานสำรวจจริง)
4. ให้มัน "เทียบกับ JS oracle" เป็นนิสัย — เหมือนเทคนิคมิเรอร์ที่เราใช้มาแล้ว

### 5.3 ตัวอย่างคำสั่งที่ดีให้ Claude Code (คัดลอกไปใช้ได้)
- *"Port `reference/FPMath.gs` to `src/survey_align/fpmath.py`. Pure functions, type hints,
  docstrings (units + sign). Then write `tests/test_fpmath.py` checking: deg_to_rad(180)=π,
  normalize_angle(-0.1)=2π−0.1, angle_diff(...). Run pytest until green. Keep it small."*
- *"Implement `coord_to_station` in `alignment.py` to match the JS reference. Use
  `tests/golden/controls.json`: every control point must return sta within 1e-3 and offset
  within 1e-3. Do not change public signatures."*
- *"Add a hypothesis property test: for random sta in range and offset in [−10,10],
  `coord_to_station(*station_to_coord(sta, offset))` recovers (sta, offset) within 1e-6 on
  tangent/circular segments."*
- *"Generate `tests/golden/` fixtures by running the JS engine in `reference/` (node) and
  dumping element table + controls to JSON. Then make the Python tests read those."*

### 5.4 คุมไม่ให้ over-engineer (รักษา SMALL)
ใส่ใน CLAUDE.md: *"Keep functions small and pure. Don't add numpy/abstractions unless a
failing test requires it. Don't refactor a passing module without a failing test first.
Match the JS oracle exactly."*

---

## 6. ความเสี่ยงและข้อควรระวัง
- **ความเที่ยงเชิงตัวเลข:** Python เป็น IEEE 754 เหมือนกัน มี `math.atan2`, `math.floor` ครบ →
  การพอร์ตจะ *ง่ายกว่า VBA* (ไม่ต้องเขียน atan2 เอง) แต่ยังต้องยืนยันด้วย golden tests
- **การกระจายของแหล่งความจริง (drift):** เมื่อ Python เป็น master ต้องตัดสินใจว่า GAS/VBA จะ
  *(ก)* แช่แข็ง/ถือเป็นของอนุพันธ์ หรือ *(ข)* ดูแลคู่ขนาน (เสี่ยง drift) — แนะนำ (ก) แล้วทยอยย้ายผู้ใช้
- **ข้อจำกัดเดิมต้องเขียนกำกับไว้:** spiral+compound ยังไม่รองรับ; inverse ที่จุดเริ่ม spiral พอดี
  เป็นเคสขอบ — ใส่เป็น docstring/known-issues และเทสต์ที่ "รู้ว่ามันเป็นแบบนี้"
- **อย่ารีบทำหน้าบ้าน** ก่อนแกนนิ่ง — เสียเวลาแก้สองที่

---

## 7. แนวทางที่ผมแนะนำ (ความเห็นแบบโค้ช)

**ทำแกนให้เป็น "ไลบรารีบริสุทธิ์ + type + tested" ก่อนเป็นอันดับหนึ่ง** ใช้ JS เดิมเป็น oracle,
ใช้ golden tests เป็นตาข่าย แล้วค่อยมี **CLI + notebook** เป็นหน้าบ้าน/สื่อสอนตัวแรก
(ได้ทั้งของใช้จริงและตำราในคราวเดียว) จากนั้นลงทุนกับ **LandXML I/O** ให้คุยกับซอฟต์แวร์อื่นได้ —
ตรงนี้คือจุดที่โปรเจกต์เปลี่ยนจาก "ของเรียน" เป็น "เครื่องมือทำงานจริง" ส่วน API/GUI/CAD ค่อยตามมา

**สามก้าวแรกที่ควรเริ่มทันที:**
1. สร้าง repo skeleton + toolchain + ใส่ `reference/` (JS + tables.json) + `CLAUDE.md` + `docs/lesson.md`
2. TDD พอร์ต `fpmath` + `wcb` พร้อม golden tests (เฟส 1)
3. TDD พอร์ต `alignment` ด้วย golden 30-element + roundtrip test (เฟส 2 = หัวใจ)

> เมื่อสามก้าวนี้เขียว อาจารย์จะมี "แกนที่พิสูจน์ได้" อยู่ในมือ — ที่เหลือคือการต่อชั้นออกไปอย่างมั่นใจ

---

## ภาคผนวก A — checklist เริ่ม repo (เฟส 0)
- [ ] `git init` + โครงโฟลเดอร์ตามข้อ 3.1
- [ ] `pyproject.toml` (hatchling) + ตั้ง ruff/mypy/pytest
- [ ] ใส่ `reference/` (คัดลอก .gs ที่ผ่าน 45/45 + `tables.json`)
- [ ] วาง `CLAUDE.md` (ย่อจากเอกสารนี้: เป้าหมาย + กติกาโค้ด + oracle + module map)
- [ ] วาง `docs/lesson.md` (บทเรียนหลักการ)
- [ ] เปิดใน VS Code → เริ่มสั่ง Claude Code ตามเฟส 1

## ภาคผนวก B — เนื้อหา CLAUDE.md (ตัวอย่างย่อ)
```
# Survey-Align — context for Claude Code
GOAL: pure, typed, tested Python core for road/highway alignment math.
PRINCIPLES: SAFE, SMALL, STABLE, MODULAR.
RULES:
- Pure functions in core; no I/O, no rounding (round only at display layer).
- Angles in radians internally; degrees/DMS only at boundaries.
- Sign: offset +right/-left of travel; radius +right/-left; tangent R=0; curvature k=1/R.
- Type hints everywhere; dataclasses for Element/State; docstrings with units+sign.
ORACLE: reference/*.gs is the validated engine (AllTests 45/45). Python MUST match it
        via golden tests in tests/golden/ (built from reference/tables.json).
WORKFLOW: TDD, bottom-up (fpmath -> wcb -> alignment -> vertical/crossfall/surface ->
          builders -> check). Small commits. Don't over-engineer or add numpy without a
          failing test. Don't change public signatures of passing modules.
KNOWN LIMITS: spiral+compound unsupported; inverse exactly at a spiral-start node is an edge case.
```

— จบแผนแม่บท —
