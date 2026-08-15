# HANDOFF: SMT — ต่อจาก Fix #1 (Group A) ไปยัง Fix #2

**วันที่เขียน:** 2026-08-03
**สถานะ:** พักเซสชัน หลังปิดจบ Fix #1 สมบูรณ์ — พร้อมเริ่ม Fix #2

---

## 1. เกิดอะไรขึ้นในเซสชันที่แล้ว (สรุปลำดับเหตุการณ์)

1. ก่อนเซสชันนี้: ตัดสินใจข้าม F.6 ที่เหลือ (B, A+D) ไปทำ **code review อิสระด้วย Fable 5**
   กับ Python core (`src/smt/`) ก่อน เพราะไม่เคยมีการรีวิวอิสระมาก่อนเลย
2. Fable 5 รีวิวเสร็จ พบ 22 findings (critical 0 / major 5 / minor 15+advisory)
   รายงานเต็มอยู่ที่ `session_logs/review_src_smt_20260802.md`
3. ตัดสินใจ (หลังชั่งน้ำหนักผลกระทบ): **แก้ Group A ทั้ง 4 ข้อ** (#1-4, บั๊กใน
   protected functions) โดยตั้งใจให้ Python core ที่แก้แล้วเป็น **oracle ใหม่**
   — `reference/*.gs` และ VBA จะต้องตามแก้ทีหลังแยกต่างหาก ไม่ใช่กลับกัน
4. เพิ่มกฎใหม่ 4 จุดใน `CLAUDE.md` (ดูหัวข้อ 2 ด้านล่าง) ก่อนเริ่มแก้จริง
5. **Fix #1 เสร็จสมบูรณ์** (ดูหัวข้อ 3) — commit + push แล้ว
6. ทดสอบด้วย **ข้อมูล Setting Out Data จริง** จาก CK1024 (compound curve 2 คู่
   + spiral 4 ประเภท) → เจอปัญหาจริงในข้อมูล (ไม่ใช่บั๊กโค้ด) → แก้ข้อมูล →
   ทดสอบผ่านสมบูรณ์ → เก็บเป็นชุดข้อมูลถาวร `test_data/AL1_*` (ดูหัวข้อ 4)
7. พักเซสชัน — ยังไม่เริ่ม Fix #2

---

## 2. กฎใหม่ใน CLAUDE.md ที่เพิ่มเซสชันนี้ (ต้องรู้ก่อนทำงานต่อ — สำคัญมาก)

ทั้งหมด commit ไปแล้วใน `ccb29b9`

1. **Oracle correction exception** (หัวข้อ "Oracle + testing"): ถ้าพิสูจน์ได้ว่า
   `reference/*.gs` เองมี defect จริง (ไม่ใช่แค่ Python พอร์ตผิด) ผ่านการรีวิวอิสระ
   — Python ที่แก้แล้วเป็น oracle ใหม่สำหรับพฤติกรรมนั้น `.gs`/VBA ต้องตามแก้
   ทีหลัง มีข้อบังคับ 5 ข้อ (บันทึกเหตุผลใน `docs/extensions.md`, dated entry ใน
   Known limits, regenerate golden fixture อย่างมีสติถ้าจำเป็น, เพิ่ม test ใหม่
   เจาะจง, ระบุ divergence ที่ยังไม่ sync ชัดเจน)
2. **Extension policy ข้อ 2 ขยายความ**: "ห้ามทำให้ test เดิมพัง" หมายถึงห้าม
   พังแบบไม่ตั้งใจ/ไม่บันทึก ถ้าจำเป็นต้อง regenerate golden fixture เพราะพิสูจน์
   แล้วว่าค่าเดิมผิด ให้ทำอย่างมีสติ + บันทึกเหตุผล (แบบเดียวกับตอนแก้ COSINE)
3. **"Verify/scratch scripts"** (ส่วนที่ 8 หัวข้อใหม่): ห้ามฝัง script หลายบรรทัด
   ใน `python -c "..."` (เปราะบางเวลาโชว์ผ่าน terminal/confirmation dialog —
   พังจริงมาแล้วรอบนี้) ให้เขียนเป็นไฟล์ `.py` แยกเสมอ เช่น
   `session_logs/tmp_verify_<เรื่อง>.py`
4. **Import convention ในสคริปต์ scratch**: ต้องใช้ `from smt....` (ตรงกับที่
   `tests/` ใช้จริง เพราะแพ็กเกจติดตั้งแบบ editable) ห้ามใช้ `from src.smt....`
   — เพราะรันเป็นไฟล์ (`python <path>.py`) sys.path จะไม่มี project root ให้
   (ต่างจาก `python -c` ที่ cwd เข้า sys.path อัตโนมัติ)

---

## 3. Fix #1 สรุปโดยละเอียด (ใช้เป็นแม่แบบกระบวนการสำหรับ #2-#4)

**บั๊ก:** `build_alignment_from_pi` (`src/smt/builders/alignment_builder.py`)
หารด้วย `sin(delta)` ไม่มี guard — delta≈0 (PI เรียงเส้นตรงพอดี มี R) ทำให้
`ZeroDivisionError` crash ทันที, delta≈π (หักกลับเกือบ 180°) ได้ geometry ขยะ
แบบเงียบสนิท (station พุ่งหลักพันล้านเมตร ไม่มี issue เตือนเลย — อันตรายกว่า
กรณีแรกมาก)

**การตัดสินใจสำคัญที่ทำไปแล้ว:**
- ทั้ง delta≈0 และ delta≈π **fallback เป็น angle-point (EXT-001) ไม่ raise**
  (ตัดสินใจร่วมกับ CK1024 แล้ว — เป็นบรรทัดฐานสำหรับ #2-#4 ด้วย เว้นแต่จะมี
  เหตุผลเฉพาะให้ raise แทน)
- **ต้องใช้ 2 threshold แยกอิสระ ไม่ใช่ threshold เดียว** — บทเรียนสำคัญที่สุด
  ของ Fix #1: `abs(sin(delta))` ค่าเดียวแยกไม่ออกว่า delta ใกล้ 0 หรือใกล้ π
  (ทั้งคู่ทำให้ sin เข้าใกล้ 0 เหมือนกัน) ทั้งที่สอง singularity มี "รัศมีอันตราย"
  ต่างกันมาก (removable vs non-removable) — ถ้า #2-#4 มี pattern คล้ายกัน
  (หลายเงื่อนไข singular พร้อมกัน) ให้ระวังจุดนี้ไว้ก่อน อย่าใช้ threshold
  เดียวรวบทุกกรณีโดยไม่พิสูจน์ก่อนว่าโอเคจริง
- Threshold ที่ใช้จริง: `fpmath.EPS=1e-9` สำหรับ δ≈0, ค่าคงที่ใหม่
  `_NEAR_PI_EPS=1e-4` สำหรับ δ≈π (ที่มา: noise floor จริงจากการปัดเศษพิกัด
  input 3 ตำแหน่งทศนิยม ที่ CK1024 ยืนยันด้วย Civil 3D ของตัวเอง ~1e-7m —
  ถ้า #2-#4 ต้องตั้ง threshold ใหม่ ให้ขอข้อมูล real-world noise floor จาก
  CK1024 แบบเดียวกัน อย่าเดาตัวเลขเอง)

**Commits (เรียงเวลา, push แล้วทั้งหมด):**
| Commit | เนื้อหา |
|---|---|
| `ccb29b9` | docs: CLAUDE.md 4 จุด (ก่อนเริ่มแก้) |
| `454b55d` | fix(#1): guard หลัก |
| `52e9a87` | docs: เติม commit hash ใน extensions.md แทน TBD |
| `4f3fc9b` | test: เพิ่มชุดข้อมูล AL1 |

**Tests:** 3 เคสใหม่ใน `TestNoCurvePI` (`tests/builders/test_alignment_builder.py`)
— `pytest -q` เต็มชุด **507 passed** (ไม่ใช่ 407 ที่เขียนผิดไว้เดิมใน CLAUDE.md
Status — ยังไม่ได้แก้ ดูหัวข้อ 6)

**Docs:** `docs/extensions.md` entry ใหม่ "Oracle Correction — build_alignment_from_pi
Singular Deflection Guard", `CLAUDE.md` Known limits entry ใหม่ — ทั้งคู่มีสูตร
พิสูจน์คณิตศาสตร์เต็ม ใช้เป็นตัวอย่างมาตรฐานความละเอียดสำหรับ #2-#4

**`.gs`/VBA:** ยัง**ไม่ sync** — เป็น known divergence ตามกฎ Oracle correction
exception ข้อ 5 (งานแยกต่างหาก ไม่ใช่ตอนนี้)

---

## 4. ชุดข้อมูลทดสอบจริง AL1 (ใหม่เซสชันนี้)

`test_data/AL1_test_alignment_PI.csv` + `test_data/AL1_test_alignment_drawing.csv`
— ข้อมูล Setting Out Data จริงจาก CK1024 ครอบคลุม compound curve 2 คู่
(R125/R125, R100/R70) + spiral 4 ประเภทพร้อมกัน (Clothoid×2, Bloss, COSINE,
SINE) — `smt build` + `smt compare-drawing` ผ่านสมบูรณ์ (gap สูงสุด ~1.8mm)

**บทเรียนสำคัญจากการทดสอบนี้:** พิกัด PI ของ spiral **ต้องเป็นจุดตัดเส้นสัมผัส
ของทั้งชุด TS-SC-CS-ST** ไม่ใช่แค่ส่วนโค้งวงกลม — ถ้าใครในอนาคตแปลง Setting
Out Data จริงมาทดสอบอีก ระวังจุดนี้ (พิกัด PI ที่ผิดแบบนี้ทำให้ error สะสมได้
หลักสิบเมตรทั้งที่โค้ดไม่มีบั๊กเลย)

---

## 5. งานที่เหลือใน Group A (#2-#4)

จาก `session_logs/review_src_smt_20260802.md`:

- **#2** (ถัดไป): `build_alignment_from_pi` ไม่เช็คว่า curve ที่สร้างขึ้นซ้อนทับ
  กันหรือไม่ — ยังไม่ได้เริ่มวิเคราะห์รายละเอียด ให้เริ่มจากอ่านหัวข้อ #2 ใน
  รายงานก่อน
- **#3**: `parse_pi_table` compound_arcs รั่วข้าม vertex boundary
- **#4**: `check_against_drawing` skip จุดที่ match ไม่ได้แบบเงียบ + ไม่มีเพดาน
  ระยะ (แตะ 2 ไฟล์: `alignment_builder.py` และ `vertical_builder.py`)

ทำทีละข้อ ไม่รวมหลายข้อในแผนเดียว (ตามที่ตกลงกันไว้ตั้งแต่ต้น)

---

## 6. งานเล็กๆ ที่ค้างไว้ (ไม่เร่งด่วน แต่อย่าลืม)

- `CLAUDE.md` หัวข้อ "Status" ยังเขียนว่า "407/407 tests passing" — ล้าสมัย
  (ตัวเลขจริงตอนนี้คือ 507+) ควรอัปเดตพร้อมกับรอบที่แก้ #2-#4 เสร็จ
- ไฟล์ untracked เก่าใน root/`test_data/`/`session_logs/` (DRAFT_plan_*,
  HANDOFF_*, test_data csvs อื่นๆ) ยังไม่ได้ triage ว่าจะเก็บ/ลบ/commit —
  ไม่กระทบงานหลัก แต่ถ้ามีเวลาว่างค่อยจัดการ

---

## 7. บทเรียน/กฎเหล็กที่ต้องยึดต่อ (สำคัญมาก — เจอปัญหาจริงมาแล้วในเซสชันนี้)

- **ขอให้ Claude Code แสดงเนื้อหา/diff จริงในแชทเสมอ** ไม่ใช่แค่ "Opened
  changes in Visual Studio Code" — เจอปัญหาที่อนุมัติแบบมองไม่เห็นเนื้อหาไม่ได้
  หลายรอบ
- **ไม่เชื่อคำสรุป/paraphrase ของ Claude Code เฉยๆ** โดยเฉพาะผล pytest —
  ต้องขอ raw output ที่ลงท้ายด้วยบรรทัด `===...===` พร้อมตัวเลขเสมอ
- **ห้ามกด "always allow"/"don't ask again"/"allow all edits" ทุกแบบ**
  ไม่มีข้อยกเว้น แม้คำสั่งจะดูปลอดภัยแค่ไหนก็ตาม ตรวจทีละครั้งเสมอ
- **`session_logs/latest.md` ต้อง append ผ่าน heredoc (`cat >>`) เท่านั้น**
  ห้ามใช้ Update/Edit tool กับไฟล์นี้เด็ดขาด (เคยลองใช้ผิดมาแล้วรอบนี้)
- **Commit message เขียนผ่าน heredoc แล้วต้อง `cat -A` ตรวจก่อน `git commit`
  เสมอ** — ตัวอักษรไทยที่ขึ้นเป็น `M-...` ใน `cat -A` เป็นเรื่องปกติ (UTF-8
  multi-byte) ไม่ใช่ปัญหา แต่ต้องเช็คว่าจบทุกบรรทัดด้วย `$` (ไม่มี `^M`/CRLF)
  และไม่มี `EOF`/`echo` หลุดเข้าไฟล์
- **ก่อน `git push` ต้องเห็น raw output ของ `git log -N --oneline` ก่อนเสมอ**
  ยืนยัน hash ตรงลำดับที่คาดก่อนค่อย push
- **สคริปต์ scratch ทั้งหมด: ไฟล์ `.py` แยก + `from smt....`** (ดูหัวข้อ 2)
- ระวัง path ที่ Claude Code พิมพ์มาเพี้ยน (ตัดตอน/ผสมชื่อไฟล์ปนกัน) —
  เจอมาแล้วหลายรอบกับคำสั่งที่มี `cd`/`&&` ยาวๆ ถ้าดูแปลกให้ขอคำสั่งเต็มซ้ำ
  ก่อนอนุมัติเสมอ

---

## 8. คำสั่งสำหรับ Claude Code — เริ่มงาน #2 (ส่งได้เลยหลัง Claude แชทยืนยัน)

```
เริ่มงานใหม่: แก้บั๊ก #2 จาก session_logs/review_src_smt_20260802.md
(build_alignment_from_pi ไม่เช็ค curve ซ้อนทับกัน) — เป็นข้อ 2 ของกลุ่ม A
(protected-function bugs #1-4) ที่ตัดสินใจแก้แล้วตั้งแต่ก่อนหน้า

อ่านรายละเอียดบั๊ก #2 จาก session_logs/review_src_smt_20260802.md ก่อน
(หาหัวข้อ #2) แล้วเขียนสคริปต์ verify แยกไฟล์ .py (ตามกฎ "Verify/scratch
scripts" ใน CLAUDE.md ส่วนที่ 8 — ห้ามใช้ python -c, import ต้องใช้
from smt.... ไม่ใช่ from src.smt....) เพื่อ reproduce ปัญหาจริงด้วยตัวอย่าง
input ที่ทำให้ curve ซ้อนทับกันได้จริง แสดง path ไฟล์ + ผล before (ปัญหาที่
เกิดขึ้นจริง) ในแชทให้ชัดเจนก่อน

ยังไม่แก้โค้ดใดๆ ทั้งสิ้น — รอ Claude (แชท) ตรวจก่อนตามมาตรฐาน
Plan-Review-Approve (มาตรฐานส่วนที่ 3 ของ CLAUDE.md) ทุกขั้นตอน
```

---

## 9. ข้อความเปิดสำหรับ Claude (แชท) เซสชันใหม่

```
สถานะล่าสุด (2026-08-03): Fix #1 (sin(delta) guard ใน build_alignment_from_pi)
ปิดจบสมบูรณ์แล้ว — commit+push ครบ 4 commits (ccb29b9, 454b55d, 52e9a87,
4f3fc9b) sync กับ origin/main แล้วทั้งหมด รายละเอียดเต็มอยู่ในไฟล์ handoff
ที่แนบมา (HANDOFF_GROUPA_FIX2_20260803.md)

ต่อไปคือ #2 จาก Group A — build_alignment_from_pi ไม่เช็คว่า curve ที่
สร้างขึ้นซ้อนทับกันหรือไม่ ทำตามกระบวนการเดียวกับ Fix #1 ทุกขั้นตอน
(Plan-Review-Approve, พิสูจน์คณิตศาสตร์ตาม Extension policy ข้อ 3, before/
after จริงจากสคริปต์ scratch แยกไฟล์ .py, test ใหม่เจาะจง, อัปเดต
docs/extensions.md + CLAUDE.md Known limits, .gs/VBA ยัง divergence ไม่ต้อง
sync ตอนนี้)

อ่าน handoff ที่แนบให้ครบก่อน โดยเฉพาะหัวข้อ 7 (บทเรียน/กฎเหล็ก) แล้วช่วย
เขียนคำสั่งเริ่มต้นให้ Claude Code ด้วย
```
