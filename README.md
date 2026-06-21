# Surveyor Micro Toolkit (SMT)

แกนคำนวณ (core engine) งานแนวเส้นทางถนน/สะพาน/ทางลาด แบบ pure + typed + tested
ออกแบบให้เป็น **แหล่งความจริงเดียว** สำหรับต่อยอดเป็น CLI / API / Excel / โน้ตบุ๊ก /
การเชื่อมต่อ (LandXML/CSV/DXF) และเป็นสื่อการเรียนรู้

แนวคิดหลัก: **SAFE - SMALL - STABLE - MODULAR**

## สถานะ

**Core engine เสร็จสมบูรณ์ — 254/254 tests ผ่าน** พอร์ตจาก Google Apps Script engine
เดิม (ผ่าน AllTests 45/45) ด้วยวินัย TDD bottom-up เทียบกับ oracle ทุกขั้นตอน

- [x] เฟส 0: โครงโปรเจกต์ + เครื่องมือ + reference (oracle) + golden fixture
- [x] เฟส 1: `fpmath`, `wcb` (คณิตศาสตร์พื้นฐาน)
- [x] เฟส 2: `alignment` (แนวราบ — หัวใจของระบบ)
- [x] เฟส 3: `vertical`, `crossfall`, `surface` (แนวดิ่ง / ยกโค้ง / ผิว 3 มิติ)
- [x] เฟส 4: `builders/alignment_builder`, `builders/vertical_builder` (สร้างแนวจาก PI/VPI)
- [x] เฟส 5: `check` (cross-check — เทียบค่าคำนวณกับค่าจากแบบ)
- [x] เฟส 6: CLI (`smt fwd` / `smt inv`) + Notebook สอนแนวราบ

ดูรายละเอียดกฎการพัฒนาและแผนต่อยอดที่ `CLAUDE.md` และ `docs/blueprint.md`

## เริ่มใช้งาน

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest                       # หรือ:  python dev_run_tests.py  (ถ้ายังไม่ลง pytest)
```

## ตัวอย่างการใช้งาน

### เป็นไลบรารี Python

```python
from smt import wcb, fpmath as fp
p = wcb.calculate_forward(20000, 10000, fp.deg_to_rad(90), 519.6152)
print(p.n, p.e)             # 20000.0  10519.6152
```

### ผ่าน CLI

```bash
pip install -e .
smt fwd elements.csv 519.615 --offset 0
smt inv elements.csv 20000 10519.6152
```

### ผ่าน Notebook (สื่อสอน)

```bash
pip install -e ".[notebook]"
jupyter notebook notebooks/01_horizontal_alignment.ipynb
```

วาดภาพ plan view ของแนวเส้นทาง ไล่สีตามชนิด element พร้อมจุดควบคุม PC/PT/SC/CS

## โครงสร้างโปรเจกต์

```
src/smt/
  fpmath.py, wcb.py            แกนคณิตศาสตร์พื้นฐาน
  alignment.py                 แนวราบ (หัวใจของระบบ)
  vertical.py, crossfall.py, surface.py   แนวดิ่ง / ยกโค้ง / ผิว 3 มิติ
  builders/                    สร้างแนวจาก PI / VPI
  check.py                     cross-check (เทียบค่าคำนวณกับค่าจากแบบ)
  cli.py                       command-line interface (smt fwd / smt inv)
tests/          เทสต์ + golden fixtures (tests/golden/tables.json)
reference/      engine JS เดิม (oracle ที่ผ่าน AllTests 45/45)
docs/           lesson.md (บทเรียนหลักการ) + blueprint.md (แผนแม่บท) + naming_convention.md
notebooks/      สื่อการสอน (01_horizontal_alignment.ipynb)
```

## เอกสารเพิ่มเติม

- `CLAUDE.md` — กฎการพัฒนา, มาตรฐานการตั้งชื่อ, สถานะโมดูล (อ่านโดย Claude Code)
- `docs/lesson.md` — บทเรียนหลักการเขียนโปรแกรมคำนวณงานสำรวจ
- `docs/blueprint.md` — แผนแม่บทและแนวทางต่อยอด
- `docs/naming_convention.md` — มาตรฐานการตั้งชื่อตัวแปร/ฟังก์ชัน