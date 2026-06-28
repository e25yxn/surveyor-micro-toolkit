# SMT (Surveyor Micro Toolkit) — context for Claude Code

GOAL: a pure, typed, tested Python **core engine** for road / highway / ramp alignment
math. This is the single source of truth from which CLI, API, Excel, notebooks, and
interop (LandXML/CSV/DXF) will derive. It is also a teaching reference.

## Principles (non-negotiable)
SAFE - SMALL - STABLE - MODULAR.

## Coding rules
- Pure functions in the core: no I/O, no global state, no side effects.
- NO rounding inside the core. Round/format only at the display/output boundary.
- Angles in **radians** internally; degrees / packed-DMS only at boundaries.
- Sign conventions: offset `+`=right of travel, `-`=left; radius `+`=right, `-`=left;
  tangent R=0; curvature `k = 1/R` (signed).
- Type hints on every function; dataclasses / NamedTuple for records.
- Docstrings state: what it does + units + sign convention + reference formula.
- Keep functions small (one job). Don't add numpy/abstractions without a failing test.

## Naming (full guide: docs/naming_convention.md)
- Anatomy (all languages): name = [verb Action] + [Target] + [Context],
  e.g. calculate_northing_from_azimuth. Context may be dropped if obvious.
- Casing (Python core): snake_case for functions/methods/variables; PascalCase for
  classes; UPPER_SNAKE_CASE for constants. (JS/VBA mirror uses camelCase for funcs/vars.)
- Approved verbs (one per concept, use consistently): calculate_ (math), get_ (lookup),
  make_ (one object), build_ (assemble many), parse_ (table->struct), normalize_,
  round_/trunc_, check_ (cross-check), is_/has_/in_ (boolean).
  Unit conversion uses the idiom <source>_to_<target> (deg_to_rad).
- Ubiquitous language: use survey terms (alignment, station, offset, azimuth/WCB,
  curvature, radius, tangent, spiral, transition, vertical_curve, grade, crossfall,
  PI, VPI, PC, PT, control_point, deviation, profile).
- Allowed abbreviations ONLY: N, E, sta, R, k, PI, VPI, PC, PT, SC, CS, TS, ST, WCB,
  LVC, dms. Spell out everything else (azimuth not az, distance not dist).
- 4 senior rules: clarity > brevity; one verb per concept; speak the expert's language;
  don't repeat the class/module name inside a method.

## Oracle + testing (how we guarantee correctness)
- `reference/*.gs` is the validated engine (passed AllTests 45/45).
  **Python MUST match oracle for all original features.**
  For features that extend beyond oracle, see Extension policy below.
- `reference/tables.json` and `tests/golden/tables.json` hold known-answer fixtures
  (30-element alignment, 31 control points, vertical table, cross-fall).
- Workflow: **TDD, bottom-up**. Write/keep golden tests, then make them green.
  Module order: fpmath -> wcb -> alignment -> vertical -> crossfall -> surface
  -> builders -> check.
- Always add a roundtrip test where it applies (forward->inverse recovers input).
- Run `pytest` (or `python dev_run_tests.py` if pytest is not installed yet).
- Don't change public signatures of passing modules; add, don't break.

## Status
All phases complete — 387/387 tests passing.
- Core engine: 9 modules ported and validated against oracle
- CLI: `smt fwd` / `smt inv` / `smt cross-check` complete
- Notebook: 01_horizontal_alignment.ipynb complete
- Extensions: EXT-001 no-curve PI (angle point) — see docs/extensions.md
- Bulk field cross-check: parse_pi_table + bulk_cross_check + CLI (3aa8e30)
- Next: LandXML I/O, web stake-out app

## Module map (.gs -> .py)
| reference (.gs)        | src/smt (.py)                  | status |
|------------------------|--------------------------------|--------|
| FPMath.gs              | fpmath.py                      | [DONE] |
| WCB.gs                 | wcb.py                         | [DONE] |
| Alignment.gs           | alignment.py                   | [DONE] |
| Vertical.gs            | vertical.py                    | [DONE] |
| CrossFall.gs           | crossfall.py                   | [DONE] |
| Surface3D.gs           | surface.py                     | [DONE] |
| AlignmentBuilder.gs    | builders/alignment_builder.py  | [DONE] |
| VerticalBuilder.gs     | builders/vertical_builder.py   | [DONE] |
| HorCheck.gs/VerCheck.gs| check.py                       | [DONE] |

## Known limits
- spiral + compound combination unsupported.
- inverse exactly at a spiral-start node is a benign edge case (matches the JS oracle).
- no-curve PI (angle point, R=None/R=0/collinear) → NOW SUPPORTED via EXT-001
  (was: KeyError/NaN in oracle; now: emits tangent element + ControlPoint 'IP')

---

# มาตรฐานการทำงานร่วมกัน (Collaboration Standard)

ข้อตกลงการทำงานระหว่าง 3 ฝ่าย: ผู้ใช้ (อาจารย์) · Claude (แชทที่ปรึกษา) ·
Claude Code (CLI ในเครื่อง) เพื่อให้สื่อสารกันตรงประเด็น ไม่สับสน ไม่เสียโควต้าโดยใช่เหตุ

---

## ส่วนที่ 1 — การบันทึก Log อัตโนมัติ (แก้ปัญหา copy จากจอ)

Claude Code ต้องทำสิ่งต่อไปนี้โดยอัตโนมัติ ไม่ต้องรอให้ผู้ใช้ขอ:

1. หลังทำงานเสร็จแต่ละหน่วย (แก้ไฟล์ / รัน test / commit) ให้ append ลงไฟล์
   `session_logs/latest.md` ด้วย Write tool
2. แต่ละรายการบันทึก: เวลา / สิ่งที่ทำ / คำสั่งที่รัน / ผล (ผ่าน-ไม่ผ่าน) / commit hash (ถ้ามี)
3. เขียนให้ผู้ใช้อ่านเข้าใจง่าย ภาษากระชับ ไม่ต้องมีศัพท์เทคนิคเกินจำเป็น

รูปแบบแต่ละรายการใน latest.md:
```
## [เวลา] หัวข้องาน
- ทำ: <อธิบายสั้นๆ>
- คำสั่ง: <command ที่รัน>
- ผล: PASS / FAIL (<จำนวน test ที่ผ่าน>)
- commit: <hash> (ถ้ามี)
- หมายเหตุ: <ถ้ามีอะไรผิดปกติ>
```

> ผู้ใช้แค่ upload `session_logs/latest.md` ให้ Claude (แชท) — ไม่ต้อง copy จาก terminal อีก

---

## ส่วนที่ 2 — รายงานตรวจสอบสถานะ (Health Check Report)

เมื่อผู้ใช้ขอ "ตรวจสถานะโปรเจกต์" หรือ "เช็คว่าเป็นเวอร์ชันล่าสุดหรือยัง" ให้ Claude Code
สร้างไฟล์ `session_logs/health_check.md` โดยรันและบันทึกผลทั้งหมดนี้:

1. `git status`                            → มีไฟล์ค้าง uncommit ไหม
2. `git log --oneline -10`                 → 10 commit ล่าสุด
3. `git log origin/main..HEAD --oneline`   → commit ที่ยังไม่ push (ว่าง = push ครบแล้ว)
4. `git status -sb` บรรทัดแรก             → local vs remote ตรงกันไหม (ahead/behind)
5. `pytest -q` บรรทัดสุดท้าย              → จำนวน test ที่ผ่าน
6. `ruff check src/` บรรทัดสรุป           → จำนวน lint error
7. `mypy` บรรทัดสรุป                      → จำนวน type error

แล้วสรุปท้ายไฟล์เป็น 1 บรรทัด: "สถานะ: สะอาด/มีงานค้าง — <รายละเอียดสั้นๆ>"

> ผู้ใช้ upload `session_logs/health_check.md` ให้ Claude (แชท) เพื่อวิเคราะห์

---

## ส่วนที่ 3 — กฎ "วางแผนก่อนทำ" (Plan-Review-Approve)

สำหรับงานที่ "แก้โค้ด" (ไม่ใช่แค่อ่าน/รายงาน) ให้ทำตามวงจรนี้เสมอ:

1. **Claude Code วางแผนก่อน** — เขียนแผนเป็นไฟล์ `session_logs/plan.md`
   ระบุ: จะแก้ไฟล์ไหนบ้าง / แก้อะไร / มีความเสี่ยงอะไร / test ที่ใช้ยืนยัน
2. **ผู้ใช้ upload plan.md ให้ Claude (แชท) รีวิว** — Claude ตรวจแผนแล้วบอกว่า
   อนุมัติได้ หรือต้องปรับอะไร
3. **เมื่อ Claude อนุมัติ ผู้ใช้จึงสั่ง Claude Code ลงมือ**
4. **ห้าม Claude Code แก้โค้ดนอกเหนือจากแผนที่อนุมัติ** ถ้าเจอเรื่องใหม่ระหว่างทาง
   ให้หยุดและรายงานก่อน

> งานประเภท "อ่าน/รายงาน" (audit, health check) ไม่ต้องผ่านวงจรนี้ ทำได้เลย

---

## ส่วนที่ 4 — กฎเหล็กด้านคุณภาพโค้ด (ใช้ทุกโปรเจกต์)

### 4.1 ความถูกต้องเชิงตัวเลข (กันค่าคลาดเคลื่อนสะสม)
- คำนวณด้วย full precision (float64) เสมอ — **ห้ามปัดเศษกลางทาง** ปัดเฉพาะตอนแสดงผล
- เทียบ float ด้วย tolerance เสมอ ห้ามใช้ `==` ตรงๆ กับทศนิยม
- มุมเก็บเป็น radian ภายใน, แปลงเป็นองศา/DMS เฉพาะตอน input/output
- กำหนด sign convention ให้ชัดและเขียนใน docstring (เช่น offset +ขวา/-ซ้าย)
- **ถ้า test ไม่ผ่านเพราะ fixture ปัดเศษ ให้แก้ที่ test ห้ามลด tolerance ของ engine**
- ใช้ oracle (เวอร์ชันที่ผ่านการพิสูจน์แล้ว) + golden test เป็นตาข่ายนิรภัย

### 4.2 การตั้งชื่อ (สรุปจาก naming_convention.md)
- ความหมาย: [กริยา Action] + [เป้าหมาย Target] + [บริบท Context]
  เช่น `calculate_northing_from_azimuth`
- การสะกด (Python): ฟังก์ชัน/ตัวแปร = snake_case, คลาส = PascalCase, ค่าคงที่ = UPPER_SNAKE_CASE
- คลังคำกริยา (เลือกคำเดียวต่อความหมาย): calculate_ (คำนวณ), get_ (ดึงค่า),
  make_ (สร้างชิ้นเดียว), build_ (ประกอบหลายชิ้น), parse_ (อ่านตาราง), check_ (ตรวจสอบ),
  is_/has_/in_ (boolean) — การแปลงหน่วยใช้ idiom `<src>_to_<dst>` เช่น deg_to_rad
- ตัวย่อที่อนุญาตเท่านั้น: N, E, sta, R, k, PI, VPI, PC, PT, SC, CS, TS, ST, WCB, LVC, dms
  นอกนั้นสะกดเต็ม (azimuth ไม่ใช่ az, distance ไม่ใช่ dist)

### 4.3 โครงสร้างโค้ด
- ฟังก์ชันในแกนเป็น pure function (ไม่มี I/O, ไม่มี side effect)
- type hints ครบทุกฟังก์ชัน, docstring บอก: ทำอะไร + หน่วย + เครื่องหมาย
- หลัก SAFE · SMALL · STABLE · MODULAR

---

## ส่วนที่ 5 — มาตรฐานการ commit (กัน PowerShell heredoc พัง)

1. เขียนข้อความ commit ลงไฟล์ `.git\smt_commit_msg.txt` ด้วย Write tool ก่อนเสมอ
2. รัน `git add <files>` แยกเป็นคำสั่งเดียว
3. รัน `git commit -F .git\smt_commit_msg.txt` แยกอีกคำสั่ง
4. **ห้ามใช้ heredoc** (`<<'EOF'` หรือ `@'...'@`) กับ git commit บน PowerShell
5. **หลัง commit ทุกครั้ง** ให้รัน `git log -1 --oneline` ตรวจ message ก่อน push
   ถ้า message ผิด ให้แก้ด้วย `git commit --amend` ก่อน push เสมอ

---

## ส่วนที่ 6 — รูปแบบการตอบของ Claude (แชท) ต่อผู้ใช้

เมื่อผู้ใช้ส่งเมนูปุ่ม (1/2/3/4) ของ Claude Code มา ให้ Claude ตอบรูปแบบนี้เท่านั้น:

```
กดเลข: X

เพราะ: <เหตุผลสั้น 1 บรรทัด>

ปุ่มอื่น:
1 = <ทำอะไร>
2 = <ทำอะไร>
3 = <ทำอะไร>
```

หลักการตอบ:
- ตอบเป็นขั้นตอน 1-2-3 ทีละขั้น **ห้ามใช้ตารางซับซ้อน**
- ภาษากระชับ ตรงประเด็น ไม่ต้องยาว
- ศัพท์เทคนิคอังกฤษให้มีคำไทยกำกับเมื่อจำเป็น
- ถ้าเป็นคำสั่งเสี่ยง (แก้ engine, ลด tolerance, คำสั่งยาวผิดปกติ) เตือนชัดเจน

---

## ส่วนที่ 7 — เมนูปุ่มที่เจอบ่อย (ผู้ใช้ตอบเองได้ ไม่ต้องถาม Claude)

1. "Do you want to proceed?" (รัน test / อ่านไฟล์ / git) → กด **1** (ปลอดภัย)
2. "Do you want to create/overwrite?" (ไฟล์ในโปรเจกต์) → กด **2** (allow all this session)
3. "Compound command contains cd..." → กด **1** (แค่เข้าโฟลเดอร์ตัวเอง)
4. เมนูมีคำว่า "don't ask again" แบบกว้าง → **เลี่ยง** กด 1 ธรรมดาแทน
5. commit ที่ใช้ heredoc / คำสั่งยาวเกิน → กด **No** แล้วสั่งใช้ Write + commit -F

> ถ้าไม่ใช่ 5 กรณีนี้ หรือไม่แน่ใจ → ค่อยถาม Claude (แชท)

---

## Model usage policy

### คำสั่งเปลี่ยน model ใน Claude Code
```
/model haiku    ← งานเบา
/model sonnet   ← งานกลาง (default)
/model opus     ← งานหนัก (ชั่วคราว แล้วกลับ sonnet)
```

### เลือก model ตามงาน
| งาน | model | mode |
|-----|-------|------|
| health check / log / git / audit | haiku | auto |
| เขียน test / review / docstring | sonnet | auto (ถ้าอนุมัติแล้ว) |
| วางแผน (plan.md) | sonnet | plan → รอ Claude รีวิว |
| พอร์ต algorithm ซับซ้อน | opus ชั่วคราว | plan → รอ Claude รีวิว |

### กฎเพิ่มเติม
- Do NOT spawn subagents unless explicitly asked.
- Claude (แชท) จะแจ้ง 📌 Model และ 📌 Mode ทุกครั้งก่อน prompt

---

## Extension policy (การปรับปรุงเกินกว่า oracle)

โปรเจกต์นี้อนุญาตให้พัฒนาให้ดีกว่า oracle เดิมได้ ภายใต้ 3 กฎ:

1. ทุกฟีเจอร์ที่เกิน oracle ต้อง mark ด้วย comment `# EXTENSION: beyond oracle`
   ในโค้ดและใน test เพื่อระบุว่าจุดนี้ไม่มี oracle คุ้มกัน
2. ห้ามทำให้ test เดิมพัง (regression = ผิดเสมอ) — ของเก่าที่ตรง oracle
   ต้องคงผลลัพธ์เดิมทุกข้อ
3. "ดีกว่า" ต้องพิสูจน์ด้วยเหตุผล + ที่มาของ golden data (คณิตศาสตร์/มาตรฐาน
   วิศวกรรม) ไม่ใช่ความรู้สึก

เมื่อมีการ extend: บันทึกเหตุผลและที่มาไว้ใน `docs/extensions.md`
