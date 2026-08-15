# HANDOFF — SMT (Surveyor Micro Toolkit) — 2026-08-14

**สำหรับ:** เปิดแชทใหม่กับ Claude Chat เพื่อทำงานต่อ
**อ่านก่อนเริ่มงานใดๆ:** โดยเฉพาะหัวข้อ 3 (กฎเหล็ก) ให้ครบทุกข้อ

---

## 1) สรุปสถานะปัจจุบัน

โปรเจกต์: https://github.com/e25yxn/surveyor-micro-toolkit
Local: `D:\My Second Project\SurveyorMicroToolkit`
เว็บแอปต้นแบบ (clasp): `D:\MyClasp_SMT_DEMO` (scriptId `1nZHagNeQJL-uCjJe0Ux-pApWgS5loJuT0NfOdRMKhoXAb9gWDHfwNjPp`)

**Git HEAD ล่าสุด (ทั้ง local และ origin/main ตรงกัน):** `929ad99`
**pytest -q เต็มชุด:** 529 passed
**เว็บแอปต้นแบบ:** deploy โค้ดล่าสุดแล้ว (`clasp push -f` สำเร็จ) + live-tested ผ่านจริง

### งานที่ปิดสมบูรณ์แล้ววันนี้ (2026-08-06 ถึง 2026-08-14)

**Group A — บั๊กใน protected function (จาก Claude Fable 5 review, `session_logs/review_src_smt_20260802.md`):**
- **#1** singular-deflection guard (`454b55d`) — sin(delta)≈0 หรือ delta≈π fallback เป็น angle point
- **#2** curve-overlap direction guard (`39df582`) — signed tangent length + `has_geometric_overlap` flag
- **#3** orphan compound-sub-row guard (`795f36b`) — raise แทน silent leak/drop
- **#4** check_against_drawing no-match reporting + station-distance ceiling (`3439a53`) + **EXT-004** adapter (`normalize_ip_names`/`add_pcc_control_points`)

**`.gs sync`** (`30be6c5`, `853b9f9`, `7ca5701`) — sync #1/#2/#3 เข้า `reference/gsheet/GS_AlignmentBuilder.gs`/`GS_PiTableParser.gs` + `clasp push` เข้าเว็บแอปต้นแบบจริง + live test ยืนยันผ่าน — **ระหว่างทางพบว่า `reference/AlignmentBuilder.gs` (top-level ไม่มี `gsheet/`) เป็นไฟล์ตาย v1.1 ไม่ใช่ไฟล์ deploy จริง เอกสารถูกแก้ให้ชี้ไฟล์ถูกต้องแล้ว**

**column-alias "STATION" + UI spinner fix** (`79d2147`, `929ad99`) — เพิ่ม `'station': 'sta'` เข้า column-alias ทั้ง Python (`table_splitter.py`) และ GAS (`GS_TableSplitter.gs`) + แก้ `Index.html::onCalcFail()` ให้เคลียร์ `calcStatus` — live-tested ผ่านจริง (`HOR_SMT_AL1`/`SMT_AL1` คำนวณสำเร็จ 33 elements ไม่มี warning อีกเลย)

---

## 2) Backlog ที่เหลือ (ไม่เร่งด่วน)

- Excel utf-8-sig/BOM handling — ยังไม่ triage
- CSV thousands-separator — **อาจได้รับการแก้ไปแล้วโดยไม่ตั้งใจ** (`HOR_01N01.csv` คำนวณสำเร็จในการทดสอบล่าสุด) ควรยืนยันให้ชัดก่อนปิด
- ไฟล์ untracked เก่าจำนวนมาก (`DRAFT_plan_*`, `HANDOFF_*` เก่า, ไฟล์ staging ชั่วคราว `session_logs/latest_md_append_*.md`, `session_logs/tmp_*`) — housekeeping รอ CK1024 ตัดสินใจเก็บ/ลบ
- **Multicurve.py solver** — ห้ามแตะ/สืบสวนเองโดยไม่มีการร้องขอ รอ CK1024 กำหนดสโคปก่อน

---

## 3) กฎเหล็ก/บทเรียน (สำคัญที่สุด — อ่านให้ครบ)

### 3.1 การอนุมัติ Claude Code
**ห้ามกด "allow all"/"don't ask again"/"Allow all actions..." เด็ดขาดไม่มีข้อยกเว้น** แม้แต่คำสั่ง read-only (`grep`/`ls`/`git log`/`cksum`) หรือแม้แต่ tool อื่นที่ไม่ใช่ bash (Claude in Chrome ก็มี "Allow all actions on [site] for this session" แบบเดียวกัน ห้ามเหมือนกัน) — อนุมัติทีละคำสั่งเสมอ อ่านเนื้อหาคำสั่งจริงก่อนอนุมัติทุกครั้ง ไม่ใช่เชื่อ/ไม่เชื่อแบบเหมารวมจากคำเตือนที่ระบบแสดง (คำเตือนบางอย่าง เช่น "cd + write", "cd + git" เป็น false positive บ่อยเมื่อ path ชัดเจนไม่กำกวม แต่ต้องอ่านเนื้อหาเองยืนยันทุกครั้ง ไม่ใช่เชื่อคำเตือนหรือไม่เชื่อคำเตือนแบบอัตโนมัติ)

### 3.2 ห้ามเชื่อคำสรุปเฉยๆ
ต้องขอ **raw output จริง** เสมอ (โดยเฉพาะ pytest ที่ลงท้าย `===...===`, `git log`/`git commit`/`cat -A`) ก่อน save ไฟล์ถาวร/protected function ต้องเห็น diff จริงเป็น text ก่อนเสมอ ไม่รับ "Opened in VS Code" — **กฎนี้ใช้แม้กับการเขียน log entry เอง ไม่ใช่แค่ตอน commit โค้ด** (เจอเคสจริงที่ log entry อ้าง commit hash/ตัวเลขที่ยังไม่ได้ยืนยันมาก่อน)

### 3.3 terminal-relay corruption
ข้อความไทยยาวๆ (และบางครั้งแม้แต่โค้ด/คำภาษาอังกฤษ) ผ่าน terminal เสียหายซ้ำๆ ได้ (ตัดคำกลางคำ, ขาด operator, ขาดวงเล็บ) วิธีแก้เรียงจากดีสุด:
1. **mechanical verification** — `grep -c`/`wc -l`/`cksum` เทียบตัวเลขที่คำนวณไว้ล่วงหน้า ดีกว่าอ่าน diff/cat -A ด้วยตาเมื่อเนื้อหายาว
2. **CK1024 อัปโหลดไฟล์จริงเข้าแชทตรง** — ดีที่สุดเมื่อต้องเทียบเนื้อหาไฟล์ทั้งไฟล์
3. **Claude Chat เขียนไฟล์ (`create_file`) ให้ดาวน์โหลดแล้ว copy วางตรงๆ** — ใช้เมื่อเนื้อหายาว/มีโค้ด+ภาษาไทยปนกันเยอะ (plan doc, docs entry, session log entry, commit message ยาว) หลีกเลี่ยงให้ Claude Code retype/compose เอง
4. ไม่แนะนำให้ Claude Code พิมพ์/compose เนื้อหายาวเองแล้วส่งผ่านแชทซ้ำๆ — พิสูจน์แล้วว่ายิ่งขอดูซ้ำยิ่งพลาดจุดใหม่ไปเรื่อยๆ ไม่ช่วยอะไรเพิ่ม เปลี่ยนเป็น apply-แล้ว-mechanical-check แทนทันทีที่เจอปัญหานี้

### 3.4 กฎเฉพาะไฟล์
- `session_logs/latest.md` — **append เท่านั้น (heredoc `cat >>`) ห้าม Update/Edit tool เด็ดขาด** ไฟล์ใหญ่มาก (2400+ บรรทัด) ห้าม regenerate ทั้งไฟล์
- commit message — เขียนผ่าน `.git/smt_commit_msg.txt` (heredoc, forward slash เท่านั้น) แล้ว `cat -A`/`wc -l`+`cksum` เช็คก่อน `-F` เสมอ
- ก่อน push ต้องเห็น raw `git log -N --oneline` ยืนยันทั้ง local/origin ตรงกัน
- `git add` **เฉพาะไฟล์ที่เกี่ยวข้องเท่านั้น ห้าม `git add -A`/`git add .` เด็ดขาด** (มีไฟล์ untracked เก่าเพียบที่ไม่ควรหลุดเข้า commit)

### 3.5 Protected functions — ต้องผ่าน Oracle correction exception
`parse_pi_table`/`build_alignment_from_pi`/`check_against_drawing` (Python) **ห้ามแก้ตรง** งานใหม่ต้องเป็น adapter แยกต่างหาก **ยกเว้น** พิสูจน์ได้ว่าเป็นการแก้ defect ที่มีอยู่จริงใน oracle (.gs) ด้วย (5 เงื่อนไข: พิสูจน์ oracle มี defect เดียวกัน, proof เชิงตรรกะ, เอกสาร, เทส, tracking divergence) — **ถ้าไม่มี oracle port เลย (เช่น #4, EXT-004) เงื่อนไขข้อ 1 เป็น N/A แต่ยังปลอดภัยกว่าเดิม ไม่ใช่ยกเว้นกฎ** ฟังก์ชันอื่นที่ไม่ใช่ 3 ตัวนี้ (เช่น `table_splitter.py`) แก้ตรงได้เลย ไม่ต้องผ่านกระบวนการนี้

### 3.6 Claude Chat มี sandbox ตรวจสอบอิสระ
ใช้ clone repo จริง + pip install + pytest ได้เอง (อย่ารอแค่เชื่อ diff ที่ paste มา) สำหรับ GAS ใช้ Node จำลอง (ต้องสร้างโครงสร้างโฟลเดอร์ตรงกับ `require('../FPMath.gs')` ที่ไฟล์คาดไว้ — ปัญหานี้เป็น Node-testing-only quirk ไม่กระทบ GAS runtime จริงเพราะ `typeof require` เป็น `undefined` เสมอบน Apps Script) ควรใช้คู่ขนานกับสิ่งที่ Claude Code รายงานเสมอ โดยเฉพาะก่อนอนุมัติแก้ protected function

### 3.7 clasp workflow เฉพาะ
- clasp project จริง 2 อัน คนละ scriptId: `D:\MyClasp_SMT_DEMO` (ต้นแบบจริงที่ deploy) กับ `D:\MyClasp_verify` (sandbox เก่า ไม่เกี่ยวกับ production — ไม่ต้องแตะ)
- ก่อน `clasp push` เช็ค `clasp status` ก่อนเสมอ
- **ต้องเทียบ `appsscript.json` (manifest) กับ Apps Script online editor ก่อน force push ทุกครั้ง** ไม่ใช่แค่ไฟล์ `.js`/`.gs` ที่ตั้งใจแก้ — เคยเจอว่า local ขาด `webapp` block (`executeAs`/`access`) ที่มีจริงบน remote เกือบ force push ทับ deployment config ทิ้ง
- `clasp run`/`clasp logs` ใช้ไม่ได้ (ไม่ได้ผูก GCP project) — ใช้ web editor (Run + Execution log) แทน
- deployment model: **ทีมงานแต่ละคน "Make a copy" เอง ไม่ใช่ URL เดียวที่ทุกคนใช้ร่วมกัน** — `clasp push` แก้แค่ต้นแบบ ไม่กระทบสำเนาที่ copy ไปแล้ว (ล่าสุดยืนยันว่ายังไม่มีใคร copy ไปใช้เลย)
- live test บน Test deployment (ไม่ใช่ production ถาวร) ผ่าน Claude in Chrome — ถ้า `select_browser` ถูกปฏิเสธไม่ทราบสาเหตุ ให้ CK1024 ทดสอบเองโดยตรงในเบราว์เซอร์แทนได้ ได้ผลเทียบเท่ากัน

### 3.8 ภาษา/สไตล์
ตอบไทยตลอด ตรงไปตรงมา ชี้ความเสี่ยงชัดก่อนอนุมัติ ไม่ผ่อนปรนกฎแม้งานจะดูเล็กหรือใกล้จบ

---

## 4) ข้อความเปิดสำหรับแชทใหม่ (ตัวอย่าง)

```
แนบ handoff (HANDOFF_GROUPA_20260814.md) มาให้ อ่านโดยละเอียดก่อน
โดยเฉพาะหัวข้อ 3 (กฎเหล็ก/บทเรียน) ให้ครบทุกข้อ แล้วช่วยสรุปว่าเข้าใจ
สถานะปัจจุบันถูกต้องหรือไม่ ก่อนจะตัดสินใจว่าจะเริ่มงานอะไรต่อจาก backlog
```
