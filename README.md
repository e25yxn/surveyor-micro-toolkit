# Surveyor Micro Toolkit (SMT)

แกนคำนวณ (core engine) งานแนวเส้นทางถนน/สะพาน/ทางลาด แบบ pure + typed + tested
ออกแบบให้เป็น **แหล่งความจริงเดียว** สำหรับต่อยอดเป็น CLI / API / Excel / โน้ตบุ๊ก /
การเชื่อมต่อ (LandXML/CSV/DXF) และเป็นสื่อการเรียนรู้

แนวคิดหลัก: **SAFE - SMALL - STABLE - MODULAR**

## สถานะ (เฟส)
- [x] เฟส 0: โครงโปรเจกต์ + เครื่องมือ + reference (oracle) + golden fixture
- [x] เฟส 1: `fpmath`, `wcb` + เทสต์ (ผ่าน 14/14)
- [ ] เฟส 2: `alignment` (หัวใจ) - ทำต่อด้วย Claude Code
- [ ] เฟส 3+: vertical / crossfall / surface / builders / check

## เริ่มใช้งาน
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest                       # หรือ:  python dev_run_tests.py  (ถ้ายังไม่ลง pytest)
```

## ตัวอย่าง
```python
from smt import wcb, fpmath as fp
p = wcb.calculate_forward(20000, 10000, fp.deg_to_rad(90), 519.6152)
print(p.n, p.e)             # 20000.0  10519.6152
```

## โครงสร้าง
```
src/smt/      แกนคำนวณ (fpmath, wcb, alignment, vertical, crossfall, surface, builders, check)
tests/        เทสต์ + golden fixtures
reference/    engine JS เดิม (oracle) + tables.json
docs/         lesson.md (บทเรียนหลักการ) + blueprint.md (แผนแม่บท) + workflow.svg
notebooks/    สื่อการสอน
```

ดูแผนเดินงานเต็มและวิธีทำงานกับ Claude Code ที่ `docs/blueprint.md` และ `CLAUDE.md`
