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
All phases complete — 407/407 tests passing.
- Core engine: 9 modules ported and validated against oracle
- CLI: `smt build` / `smt station-to-coord` / `smt coord-to-station` /
       `smt cross-check` / `smt compare-drawing` / `smt fit-radius` complete
- Notebook: 01_horizontal_alignment.ipynb + 02_alignment_fitting.ipynb complete
- Extensions: EXT-001 no-curve PI (angle point) — see docs/extensions.md
- Extensions: EXT-002 radius optimisation (fit_radius, Nelder-Mead) — see docs/extensions.md
- VBA Engine: 5 modules ported to Excel VBA — see reference/vba/README.md
- Next: LandXML I/O, SMT_Surface.bas, S7b interactive notebook

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
| —                      | optimizer.py                   | [DONE] (EXT-002) |

## VBA Engine map (reference/vba/)
| VBA Module           | Port จาก Python          | Functions |
|----------------------|--------------------------|-----------|
| SMT_Core.bas         | fpmath.py + wcb.py       | SMT_Pi, SMT_DegToRad, SMT_RadToDeg, SMT_NormalizeAngle, SMT_AngleDiff, SMT_Azimuth, SMT_Distance, SMT_CalcForward, SMT_CalcOffset |
| SMT_Alignment.bas    | alignment.py + WCBatSta  | SMT_StaToN, SMT_StaToE, SMT_CoordToSta, SMT_CoordToOffset, SMT_WCBatSta |
| SMT_Vertical.bas     | vertical.py              | SMT_Elevation |
| SMT_Crossfall.bas    | crossfall.py             | SMT_CrossfallLeft, SMT_CrossfallRight |
| SMT_Geometry.bas     | LocalCoord + Rotation3D  | SMT_LocalToN, SMT_LocalToE, SMT_GlobalToY, SMT_GlobalToX, SMT_RotX, SMT_RotY, SMT_RotZ |

**Import order ใน Excel:** SMT_Core → SMT_Alignment → SMT_Vertical → SMT_Crossfall → SMT_Geometry

**Named Ranges ที่ต้องสร้างใน Excel:**
- `SMT_Elements` = elements_output.csv data (B4:I34 ไม่รวม header, ไม่รวม index)
- `SMT_Vertical` = vertical table data (C4:I10 ไม่รวม index column)
- `SMT_Crossfall` = crossfall table data (C4:H12 ไม่รวม index column)

## Known limits
- spiral + compound combination unsupported.
- inverse exactly at a spiral-start node is a benign edge case (matches the JS oracle).
- no-curve PI (angle point, R=None/R=0/collinear) → NOW SUPPORTED via EXT-001
- fit_radius requires scipy: `pip install -e ".[optimize]"`
- VBA Named Range ต้องไม่รวม index column และ header row
- `_flush_pending` (builders/alignment_builder.py) ทิ้งค่า R ของแถว PI แบบเงียบเมื่อมี compound sub-row ตามมา
  ยังไม่ได้แก้ พบเมื่อ 2026-07-03
- `test_data/SettingOutTest.csv` PI7 ได้รับผลกระทบจากบั๊กข้างต้น ห้ามใช้ PI7 อ้างอิงจนกว่าจะแก้ไฟล์
- transition COSINE แก้แล้วเมื่อ 2026-07-05 ให้ใช้สูตรปิด Civil 3D Sine Half-Wave แทน Simpson เดิม
  (เดิมต่าง ~3 ซม. ที่ R=900 L=100) ดู session_logs/plan_cosine_sinehalfwave_fix.md และ
  session_logs/investigate_sinehalfwave_formula.md — ยังมี known limitation ย่อยที่ยังไม่แก้:
  x≈s เป็นค่าประมาณ (คลาดเคลื่อนหลักมิลลิเมตรที่ d เท่ากับ L), SPOUT mid-curve ยืนยันด้วย
  boundary invariant เท่านั้น, LandXML totalX รายงานค่า L ไม่ใช่ X จริง (รายละเอียดใน
  alignment.py docstring "Known limitations")
- alignment_builder.py::_build_curve_sub_elements สมมติมุมเลี้ยว spiral ด้วยสูตรเชิงเส้น
  theta เท่ากับ Ls หารสองเท่าของ R ซึ่งไม่ตรงกับ COSINE closed-form ใหม่อีกต่อไป (ตรงเป๊ะเฉพาะ
  CLOTHOID/BLOSS/SINE) ทำให้กลุ่มโค้ง COSINE ที่สร้างผ่าน build_alignment_from_pi มีมุมเลี้ยว
  จริงคลาดเคลื่อนเล็กน้อย (~0.005 องศาที่ R=900 L=100 ยืนยันแล้ว) ยังไม่แก้ อยู่นอกขอบเขตแผน
  แก้ COSINE รอบนี้ ดู session_logs/investigate_cosine_builder_mismatch_20260705.md
- spiral บวก compound ยังไม่รองรับ รอออกแบบ multicurve solver ก่อนตัดสินใจ

## Civil 3D Interop ground truth references
- `smt-test1.xml` คือ Civil 3D export จริง 7 spiral types ที่ R=900 L=100
- `AL_compound.xml` บวก `compound_curve.csv` บวก `so_compound_curve.csv` คือ compound curve ground truth
  R=30 ไปยัง R=45 ยืนยันตรงกับ SMT output ต่ำกว่า 1 มิลลิเมตร เมื่อ 2026-07-03
- `py-1.xml` คือ Civil 3D export ใช้อ้างอิง LandXML attribute format

## Spiral formula verification methodology
การยืนยันสูตร spiral ใหม่เทียบ Civil 3D ต้องมี ground truth อย่างน้อย 2 ชุดที่ R หรือ L ต่างกัน ต่อ 1 shape
ก่อนสรุปว่าสูตรถูกต้อง จุดข้อมูลเดียวยืนยันได้แค่ค่าคงที่ ไม่ยืนยัน functional form ทั้งเส้น

## Roadmap
- Compound curve จะใช้ multicurve.py แยกเป็น solver คำนวณ floating curve length จาก R และมุมเบี่ยงรวม
  ก่อนกรอกตาราง แทนการแก้ CSV parser
- แผนอนาคต auto-derive เครื่องหมาย R จาก azimuth หรือ deflection change ต้อง backward compatible
  คือ R ลบยังใช้ได้เหมือนเดิม ส่วน R บวกให้คำนวณทิศทางเอง
- แผนอนาคต แยก `_shape_integral` ออกจาก alignment.py เป็นไฟล์ curvature.py เพื่อรองรับ Civil 3D spiral type
  เพิ่มในอนาคตโดยไม่กระทบ integrator

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
4. ทุกครั้งที่เขียนแผนลงไฟล์ (plan.md หรือชื่ออื่น) ต้องแสดงชื่อไฟล์ใน terminal ให้ชัดเจน
   ก่อนแสดงเมนูทางเลือก เช่น: "แผนบันทึกแล้วที่ session_logs/plan_20260628_1806.md —
   กรุณา upload ไฟล์นี้ให้ Claude (แชท) ตรวจก่อนกดทางเลือก"
   ห้ามกด Yes ทันทีโดยไม่ให้ Claude (แชท) ตรวจก่อน — กฎนี้ใช้ทั้งใน plan mode และ auto mode

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

1. `git status`
2. `git log --oneline -10`
3. `git log origin/main..HEAD --oneline`
4. `git status -sb` บรรทัดแรก
5. `pytest -q` บรรทัดสุดท้าย
6. `ruff check src/` บรรทัดสรุป
7. `mypy` บรรทัดสรุป

แล้วสรุปท้ายไฟล์เป็น 1 บรรทัด: "สถานะ: สะอาด/มีงานค้าง — <รายละเอียดสั้นๆ>"

---

## ส่วนที่ 3 — กฎ "วางแผนก่อนทำ" (Plan-Review-Approve)

สำหรับงานที่ "แก้โค้ด" (ไม่ใช่แค่อ่าน/รายงาน) ให้ทำตามวงจรนี้เสมอ:

1. **Claude Code วางแผนก่อน** — เขียนแผนเป็นไฟล์ `session_logs/plan_YYYYMMDD_HHMM.md`
   ระบุ: จะแก้ไฟล์ไหนบ้าง / แก้อะไร / มีความเสี่ยงอะไร / test ที่ใช้ยืนยัน /
   ตัวอย่าง input จริง → output ที่คาดหวังอย่างน้อย 2-3 แถว
   แล้วแสดงข้อความใน terminal ว่า "แผนบันทึกแล้วที่ <ชื่อไฟล์> — กรุณา upload ให้ Claude (แชท) ตรวจก่อนกดทางเลือก"
2. **ผู้ใช้ upload plan file ให้ Claude (แชท) รีวิว**
3. **เมื่อ Claude อนุมัติ ผู้ใช้จึงสั่ง Claude Code ลงมือ**
4. **ห้าม Claude Code แก้โค้ดนอกเหนือจากแผนที่อนุมัติ**

**กฎการรีวิวแผนของ Claude (แชท):** ก่อนอนุมัติแผนใดๆ ที่เกี่ยวกับ CSV หรือ file format
ต้องให้ผู้ใช้ upload ไฟล์จริงมาให้ Claude (แชท) อ่านก่อน ห้ามอนุมัติโดยเชื่อตามที่แผนบอก

> งานประเภท "อ่าน/รายงาน" (audit, health check) ไม่ต้องผ่านวงจรนี้ ทำได้เลย

---

## ส่วนที่ 4 — กฎเหล็กด้านคุณภาพโค้ด

### 4.1 ความถูกต้องเชิงตัวเลข
- คำนวณด้วย full precision (float64 / Double) เสมอ — ห้ามปัดเศษกลางทาง
- เทียบ float ด้วย tolerance เสมอ ห้ามใช้ == ตรงๆ กับทศนิยม
- มุมเก็บเป็น radian ภายใน แปลงที่ boundary เท่านั้น
- กำหนด sign convention ให้ชัดและเขียนใน docstring/comment

### 4.2 การตั้งชื่อ (Python + VBA)
- Python: snake_case, prefix ตาม verb catalog
- VBA: PascalCase, prefix `SMT_` ทุก function, `Option Explicit` ทุกไฟล์
- ตัวย่อที่อนุญาตเท่านั้น: N, E, sta, R, k, PI, VPI, PC, PT, SC, CS, TS, ST, WCB, LVC, dms

### 4.3 VBA เฉพาะ
- `Dim` ทุกตัวแปรด้วย `As Double` หรือ `As Long` ห้ามใช้ `Single` หรือ `Integer`
- ห้ามใช้ `Mod` กับ Double ใช้ `SMT_FloorMod` แทน
- `SMT_Atan2` ต้อง duplicate ในแต่ละ module (VBA ไม่ share Private ข้าม module)
- คำนวณ `cosA/sinA` ครั้งเดียวก่อน loop ห้ามคำนวณใน loop
- ทุกครั้งที่แก้สูตรคำนวณใน alignment.py โดยเฉพาะ `_shape_integral` ต้องอัปเดต SMT_Core.bas และ
  SMT_Alignment.bas ให้ตรงกันในรอบเดียวกัน แล้วทดสอบใน Excel จริง ห้ามปล่อยให้ VBA ค้างสูตรเก่า

---

## ส่วนที่ 5 — มาตรฐานการ commit

1. เขียน commit message ลงไฟล์ `.git\smt_commit_msg.txt` ด้วย Write tool ก่อนเสมอ
2. รัน `git commit -F .git\smt_commit_msg.txt`
3. ห้ามใช้ heredoc บน PowerShell
4. หลัง commit รัน `git log -1 --oneline` ตรวจก่อน push เสมอ

---

## ส่วนที่ 6 — รูปแบบการตอบของ Claude (แชท)

- ตอบเป็นขั้นตอน 1-2-3 ทีละขั้น ห้ามใช้ตารางซับซ้อน
- ภาษากระชับ ตรงประเด็น
- ถ้าเป็นคำสั่งเสี่ยง เตือนชัดเจน

---

## ส่วนที่ 7 — เมนูปุ่มที่เจอบ่อย

1. "Do you want to proceed?" → กด **1** (ปลอดภัย)
2. "Do you want to create/overwrite?" → กด **2** (allow all this session)
3. "Compound command contains cd..." → กด **1**
4. เมนูมีคำว่า "don't ask again" แบบกว้าง → เลี่ยง กด 1 ธรรมดา
5. commit ที่ใช้ heredoc → กด **No** แล้วสั่งใช้ Write + commit -F

---

## ส่วนที่ 8 — Smoke test ก่อน push และ CLI naming

### Smoke test ก่อน push
หลัง commit ทุกครั้งที่มีไฟล์ input จริง ต้องรัน smoke test ด้วยไฟล์จริงก่อน push เสมอ

### CLI naming convention
- `station-to-coord`, `coord-to-station`, `cross-check`, `build`, `compare-drawing`, `fit-radius`
- ห้ามใช้ตัวย่อ เช่น fwd, inv, xc

---

## Model usage policy

| งาน | model | mode |
|-----|-------|------|
| health check / log / git / audit | haiku | auto |
| เขียน test / review / VBA module | sonnet | auto (ถ้าอนุมัติแล้ว) |
| วางแผน (plan.md) | sonnet | plan → รอ Claude รีวิว |
| พอร์ต algorithm ซับซ้อน | opus ชั่วคราว | plan → รอ Claude รีวิว |

---

## Extension policy

1. ทุกฟีเจอร์ที่เกิน oracle ต้อง mark ด้วย comment `# EXTENSION: beyond oracle`
2. ห้ามทำให้ test เดิมพัง
3. "ดีกว่า" ต้องพิสูจน์ด้วยเหตุผล + ที่มาคณิตศาสตร์/มาตรฐานวิศวกรรม
4. งานปรับให้ตรง Civil 3D สำหรับ LandXML interop นับเป็น oracle อีกชั้นหนึ่ง แยกจาก reference .gs เดิม
   ต้องอ้างอิงไฟล์ Civil 3D ground truth จริงเสมอ ห้ามเดาสูตรจากความจำ

เมื่อมีการ extend: บันทึกเหตุผลและที่มาไว้ใน `docs/extensions.md`
