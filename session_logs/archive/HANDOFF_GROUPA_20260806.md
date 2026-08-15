# HANDOFF — Surveyor Micro Toolkit (SMT), Group A bug-fix work
**วันที่:** 2026-08-06
**สถานะ:** #2 ปิดจบสมบูรณ์ (commit + push แล้ว) — พร้อมเริ่มงานถัดไปจาก backlog

---

## 1. บริบทโปรเจกต์ + workflow

- **SMT (Surveyor Micro Toolkit)** — pure Python horizontal road alignment engine พอร์ตมาจาก reference implementation (Google Apps Script `.gs` + Excel VBA เป็น oracle) — repo สาธารณะที่ `https://github.com/e25yxn/surveyor-micro-toolkit`
- **สามฝ่ายทำงานร่วมกัน:** CK1024 (เจ้าของ/ผู้ตรวจอนุมัติ) ↔ **Claude Chat** (โค้ช/วางแผน/ตรวจสอบ) ↔ **Claude Code** (ผู้ลงมือทำจริงใน VS Code/terminal)
- **กฎเหล็ก: Plan-Review-Approve เข้มงวด** — CK1024 ตรวจทุกขั้นตอนของ Claude Code ทีละขั้น ไม่ batch รวมกัน
- **Protected functions ห้ามแก้ตรงๆ:** `parse_pi_table`, `build_alignment_from_pi`, `check_against_drawing` — งานใหม่ต้องเป็น adapter ห่อไว้ด้านหน้า **ยกเว้น** เข้าเงื่อนไข **"Oracle correction exception"** (ดูกฎเต็มใน `CLAUDE.md`) ซึ่งต้องมี: (1) พิสูจน์ว่า `reference/*.gs` มี defect เดียวกันจริง (2) พิสูจน์ทางคณิตศาสตร์ (3) เอกสารใน `docs/extensions.md` (4) เทสใหม่ (5) ติดตาม divergence ที่ยังไม่ sync

---

## 2. เพิ่งปิดจบ: Bug #2 (curve-overlap direction guard)

**เส้นเรื่องเต็ม** (รายละเอียดทั้งหมดอยู่ใน `docs/extensions.md` entry "Oracle Correction — build_alignment_from_pi Curve-Overlap Direction Guard" และ `session_logs/latest.md` entry ล่าสุด):

1. Reproduce บั๊กเดิม (`build_alignment_from_pi` ใช้ unsigned distance วางตำแหน่ง tangent element ระหว่าง PI ทำให้โค้งซ้อนทับกันไม่ถูกตรวจจับ)
2. Implement threshold=A ตามแผน (`session_logs/plan_20260804_2014.md`) — raw `tan_len_signed < 0`
3. รันกับข้อมูลจริง 2 ชุด (`test_data/AL1_test_alignment_PI.csv`, `test_data/HOR_01N01.csv`) เจอ noise floor จริง 0.5-1.6mm จากพิกัดปัดเศษ → threshold=A false-positive
4. เปลี่ยนเป็น threshold=B: `TOL_METERS = 0.02` (2ซม.)
5. **เจอ regression ที่ไม่คาดคิด**: `optimizer.py::fit_radius` ผูกกับ `issues` เป็น hard validity constraint มาก่อนโดยไม่รู้ตัว — แก้ด้วยการเพิ่ม `BuildResult.has_geometric_overlap` (strict flag แยกจาก `issues`)
6. สืบสวน **#2b** (EP-tangent branch, สงสัยว่ามี tangency-continuity bug แบบเดียวกัน) — **พิสูจน์แล้วว่าไม่ใช่บั๊ก** (kink = 0.000000000° ทุกเคสที่ทดสอบ, หลักการ collinearity เดียวกับ #2 กลับด้าน)
7. เขียนเอกสารครบ 3 ไฟล์ (`docs/extensions.md`, `CLAUDE.md`, `session_logs/latest.md`) — ผ่านการตรวจหลายรอบ
8. Commit 2 ครั้ง + push สำเร็จ

**สถานะสุดท้าย:**
- `origin/main` = local = commit `d19420d` (ตามด้วย `39df582` ก่อนหน้า)
- `pytest -q` เต็มชุด = **514 passed**
- `docs/extensions.md`, `CLAUDE.md` (Status header 514/514 + Known limits bullet ใหม่), `session_logs/latest.md` ครบถ้วนตรวจสอบแล้ว

---

## 3. กฎที่พิสูจน์แล้วว่าจำเป็น — ใช้ตั้งแต่ข้อความแรกของแชทใหม่

### 3.1 การอนุมัติ tool call ของ Claude Code
- **ห้ามเลือก "Yes, allow all edits during this session" หรือ "don't ask again" เด็ดขาด ไม่มีข้อยกเว้น** — ไม่ว่าจะดูเสี่ยงต่ำแค่ไหน (แม้แต่ `grep`/`ls` อ่านอย่างเดียว)
- คำเตือนแปลกๆ ของ tool ("Parser skipped input...", "Contains brace with quote character...", "Redirect target contains $(cmd)...") **มักเป็น false positive** กับ heredoc/multi-statement/ตัวแปร shell ธรรมดา — แต่ต้องอ่านเนื้อหาคำสั่งเองทุกครั้งเพื่อยืนยันก่อนอนุมัติ ไม่ใช่เชื่อ/ไม่เชื่อแบบ blanket

### 3.2 ห้ามเชื่อคำสรุปของ Claude Code เฉยๆ
- ต้องขอ **raw output จริง** เสมอ (โดยเฉพาะผล pytest ที่ลงท้าย `===...===`) ไม่รับ paraphrase
- ก่อน save ไฟล์ใดๆ (โดยเฉพาะไฟล์ถาวร/protected function) **ต้องเห็นเนื้อหา diff จริงเป็น text ในแชทก่อนเสมอ** ไม่รับแค่ "Opened changes in VS Code" / "Do you want to make this edit?"

### 3.3 ปัญหา terminal-relay ที่เจอซ้ำตลอดเซสชันก่อน — และวิธีแก้ที่พิสูจน์แล้วว่าได้ผล
- ข้อความยาว (โดยเฉพาะภาษาไทย) ที่ paste ผ่าน terminal **เสียหายซ้ำๆ** (ตัดกลางคำ, ยุบหลายบรรทัดเป็นบรรทัดเดียว) — บางครั้งเกิดจาก terminal เอง บางครั้งเกิดจาก Claude Code "พิมพ์ใหม่จากความจำ" แทนที่จะ copy จากไฟล์จริง
- **วิธีแก้ที่ได้ผลดีที่สุด (เรียงจากดีสุด):**
  1. **Mechanical verification** (ดีที่สุด): ให้ Claude Code ใช้ `cat`/`sed`/`cksum` เทียบไฟล์แบบ byte-for-byte แทนการพิมพ์/paste เนื้อหาผ่านแชท — เช่น `wc -l` เช็คจำนวนบรรทัดรวมตรงตามเลขคณิต, `cksum` เทียบไฟล์สองไฟล์ว่าตรงกันเป๊ะ ก่อน `cp` ทับไฟล์จริง
  2. **อัปโหลดไฟล์ตรงจาก CK1024** — เมื่อ Claude Code เขียนไฟล์ลง scratchpad แล้ว ให้ CK1024 อัปโหลดไฟล์นั้นเข้าแชทตรงๆ ให้ Claude Chat ตรวจ (ไม่ผ่านการ retype ใดๆ)
  3. **ไม่แนะนำ**: การ paste/retype เนื้อหายาวผ่านข้อความแชทตรงๆ (เสี่ยงพังซ้ำ)

### 3.4 กฎเฉพาะไฟล์
- `session_logs/latest.md`: append เท่านั้น (heredoc `cat >>` หรือ `cat fileA fileB >> target` แบบ mechanical) **ห้ามใช้ Update/Edit tool หรือ `cp` เขียนทับทั้งไฟล์เด็ดขาด**
- Commit message: เขียนผ่าน heredoc ลง `.git/smt_commit_msg.txt` แล้ว `cat -A` ตรวจ (ไม่มี `^M`, จบด้วย `$` ล้วน) ก่อน `git commit -F` ทุกครั้ง
- **ห้าม `python -c` แบบหลายบรรทัดเด็ดขาด** — ใช้ไฟล์ `.py` แยกต่างหาก หรือ bash ธรรมดา (`tail`, `xxd`, `grep`)
- ก่อน `git push` ทุกครั้ง ต้องเห็น raw `git log -N --oneline` ยืนยันทั้ง local และ origin/main ก่อน

### 3.5 Verify/scratch scripts
- ต้องเป็นไฟล์ `.py` แยกต่างหาก (ไม่ใช่ `python -c`)
- Import ต้องเป็น `from smt....` **ไม่ใช่** `from src.smt....`

### 3.6 Claude Chat มีความสามารถตรวจสอบอิสระของตัวเอง — ใช้ให้เป็นประโยชน์
Claude Chat ดาวน์โหลด repo จริงจาก GitHub (`codeload.github.com` tarball), `pip install -e .`, รัน/แก้/pytest ได้เองในเครื่องแบบ sandbox — **ควรใช้วิธีนี้ตรวจสอบคู่ขนานกับสิ่งที่ Claude Code รายงานเสมอ** โดยเฉพาะก่อนอนุมัติแก้ protected function หรือก่อนเชื่อผลลัพธ์ตัวเลขที่จะเข้าเอกสารถาวร — จับปัญหาได้หลายครั้งที่การอ่าน text เฉยๆ ไม่มีทางเห็น (เช่น test class ไปอยู่ผิด class เพราะเลขบรรทัดอ้างอิงผิด, ตัวเองมีบั๊กในสคริปต์ verify ที่ทำให้สรุปผิด)

### 3.7 ภาษา + สไตล์การสื่อสาร
CK1024 สื่อสารเป็นภาษาไทย — Claude Chat ตอบเป็นภาษาไทยตลอด ให้คำแนะนำแบบตรงไปตรงมา ชี้ปัญหาความเสี่ยงชัดเจนก่อนอนุมัติ ไม่ผ่อนปรนกฎแม้จะดูเป็นงานเล็กหรือใกล้จบแล้วก็ตาม

---

## 4. Backlog ที่ยังไม่เริ่ม (ลำดับไม่ได้บังคับ)

| รายการ | รายละเอียด |
|---|---|
| **#3** | `parse_pi_table` — compound sub-row รั่วข้าม vertex boundary |
| **#4** | `check_against_drawing` — skip จุดที่จับคู่ไม่ได้แบบเงียบๆ + ไม่มีเพดานระยะ (แตะ `alignment_builder.py` + `vertical_builder.py`) |
| **#5** | CSV utf-8-sig/BOM handling bug |
| **`.gs` sync สำหรับ #2** | `reference/AlignmentBuilder.gs:122-123` ยังมี unsigned-distance bug เดิม ไม่มี `tan_len_signed`/`TOL_METERS`/`has_geometric_overlap` เลย — known divergence ที่บันทึกไว้แล้วใน `docs/extensions.md` แต่ยังไม่ sync จริง |
| **Excel thousands-separator parser gap** | `parse_pi_table` อ่าน CSV ที่มีคอมม่าคั่นหลักพันแบบ Excel (เช่น `"1,537,796.012"`) ไม่ได้ — พบระหว่างตรวจ `HOR_01N01.csv`, ยังไม่ triage |
| **`test_data/HOR_01N01.csv`** | มีอยู่ในเครื่อง CK1024 พร้อมคอมม่าคั่นหลักพันดิบ ยังไม่ clean เป็นไฟล์ทดสอบถาวรแบบ AL1 — ต้องตัดสินใจว่าจะทำเป็น fixture ถาวรหรือแค่หลักฐานอ้างอิง |
| **ไฟล์ untracked เก่า** | หลายไฟล์ที่ค้างมานาน (`DRAFT_plan_*`, `HANDOFF_*` เก่า, `session_logs/tmp_diag_*`/`tmp_diff_*`, `test_data/SettingOutTest*` ฯลฯ) ยังไม่ triage เก็บ/ลบ/commit |
| **`test_data/AL1_test_alignment_drawing.csv`** | มีการแก้ format ตัวเลข STA (cosmetic, ไม่เกี่ยวกับ #2) ค้างอยู่ ยังไม่ commit |
| **Multicurve.py solver** | ต้องรอ CK1024 กำหนดสโคปก่อน ห้ามสืบสวนเองโดยไม่มีการร้องขอ |

---

## 5. ข้อความเปิดสำหรับแชทใหม่ (ให้ CK1024 พิมพ์เป็นข้อความแรก)

```
แนบ handoff (HANDOFF_GROUPA_20260806.md) มาให้ อ่านโดยละเอียดก่อน
โดยเฉพาะหัวข้อ 3 (กฎเหล็ก/บทเรียน) ให้ครบทุกข้อ แล้วช่วยสรุปว่าเข้าใจ
สถานะปัจจุบันถูกต้องหรือไม่ ก่อนจะตัดสินใจว่าจะเริ่มงานอะไรต่อจาก backlog
```

---

## 6. คำสั่งสำหรับ Claude Code (ให้ CK1024 พิมพ์ในเซสชัน Claude Code ใหม่)

```
กลับมาทำงานต่อในโปรเจกต์ SMT — ก่อนเริ่มงานใหม่ใดๆ ให้ยืนยันสถานะปัจจุบัน
ให้ตรงกับที่ตกลงไว้ก่อน:

1. git log -3 --oneline (คาดว่า HEAD คือ d19420d ตามด้วย 39df582 แล้วก็
   4f3fc9b)
2. git status (คาดว่าตรงกับสถานะที่ HANDOFF ระบุไว้ — มีแค่
   test_data/AL1_test_alignment_drawing.csv เป็น modified ไม่ staged
   และไฟล์ untracked เดิมที่ค้างมานาน ไม่มีอะไรใหม่)
3. pytest -q เต็มชุด (คาดว่า 514 passed)

แสดง raw output ทั้ง 3 คำสั่งในแชท ยังไม่ต้องเริ่มแก้ไขหรือทำงานใดๆ
เพิ่มเติมจนกว่าจะได้รับคำสั่งถัดไปว่าจะเริ่มจาก backlog รายการไหน (ดู
หัวข้อ 4 ของ HANDOFF_GROUPA_20260806.md)
```

---

## 7. ไฟล์อ้างอิงสำคัญ

- `CLAUDE.md` — กฎทั้งหมดของโปรเจกต์ (มาตรฐาน 8 ข้อ, Oracle correction exception, VBA/GAS divergence tracking)
- `docs/extensions.md` — เอกสาร Oracle correction ทุกรายการ (Singular Deflection Guard, Curve-Overlap Direction Guard)
- `session_logs/latest.md` — log ประวัติทุก session แบบละเอียด (heredoc-append only)
- `session_logs/review_src_smt_20260802.md` — รายงาน review เต็มที่เป็นต้นทางของ #2-#5 ทั้งหมด
- `session_logs/plan_20260804_2014.md` — แผนของ #2 (threshold=A ตอนแรก, ก่อนพบว่าต้องเปลี่ยนเป็น B)
