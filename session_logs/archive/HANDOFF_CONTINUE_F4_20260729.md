# HANDOFF — ต่อ Session F.4 ในแชทใหม่
**เขียน 2026-07-29 — ส่งต่อกลางเซสชัน F.4 (ยังไม่จบ) เพื่อประหยัด token**

---

## 0. บริบทของ handoff นี้

ต่างจาก handoff ของ F.3 (ที่ส่งต่อตอนจบ session สะอาดๆ) — รอบนี้ส่งต่อ
**กลาง F.4 ที่ยังไม่เสร็จ**: โค้ดเขียนครบแล้ว ตรวจผ่านแล้ว `clasp push`
สำเร็จแล้ว แต่**ยังไม่ได้ทดสอบจริงผ่าน Test deployments และยังไม่ commit
git** งานแรกของแชทใหม่คือทดสอบให้ผ่านตาม checklist แล้วค่อย commit — ไม่ใช่
เขียนโค้ดใหม่

**การเปลี่ยนแปลง workflow ที่ทำไปพร้อม handoff นี้**: เลิกใช้
`BUNDLE_gsheet.md`/`BUNDLE_python_core.md` แล้ว (เคยพบว่าเก่าไม่ทันโค้ดจริง
+ กิน token เกินจำเป็นเพราะไฟล์แนบแบบ `.md` ถูกโหลดเข้า context เต็มจำนวน
อัตโนมัติไม่ว่าจะใช้จริงหรือไม่) — จากนี้ไปแนบไฟล์จริง (`.gs`/`.js`/`.html`)
เฉพาะไฟล์ที่เกี่ยวกับงานจริงเท่านั้น ไฟล์ engine เดิมที่ไม่ได้แตะไม่ต้องแนบซ้ำ

---

## 1. ไฟล์ที่ต้องอัปโหลดในแชทใหม่ (7 ไฟล์)

**เอกสารสถานะ (living docs — อัปเดตแล้วพร้อม handoff นี้):**
1. `PROJECT_STATE.md`
2. `CLAUDE.md`
3. `DEPENDENCY_MAP.md`

**ไฟล์ F.4 ที่เขียน/แก้แล้ว รอทดสอบ+commit (แนบไฟล์จริงจากดิสก์ ไม่ paste):**
4. `reference/gsheet/GS_Pipeline.gs` (ใหม่)
5. `reference/gsheet/GS_SheetExport.gs` (ใหม่)
6. `D:\MyClasp_SMT_DEMO\TestDrive.js` (แก้ — ลบ 2 ฟังก์ชันที่ย้ายออก)
7. `reference/gsheet/Index.html` (แก้ — ผูกปุ่มคำนวณ)

**ไม่ต้องแนบ**: `FPMath.gs`, `WCB.gs`, `GS_Alignment.gs`,
`GS_AlignmentBuilder.gs`, `GS_TableSplitter.gs`, `GS_PiTableParser.gs`,
`GS_ElementTable.gs`, `GS_CrossCheck.gs`, `GS_DriveWalker.gs` — ไม่ถูกแตะใน
F.4 เลย และ memory มีบันทึกละเอียดอยู่แล้วว่าแต่ละไฟล์ verify อะไรมายังไง
(ถ้าจำเป็นต้องดูจริงๆ ค่อยขอเป็นไฟล์เดี่ยวทีหลัง)

---

## 2. สถานะปัจจุบัน (ณ 2026-07-29 กลาง F.4)

- ✅ แผน F.4 อนุมัติแล้ว (`DRAFT_plan_session_F4_calculate_pipeline.md`)
- ✅ เขียนโค้ดครบ 4 ไฟล์ ตรวจผ่านจาก Claude Chat ทุกไฟล์ (เทียบไฟล์จริงจาก
  ดิสก์ ไม่ใช่แค่ preview ในแชท — preview พิสูจน์แล้วว่าไม่น่าเชื่อถือกับ
  โค้ดยาวๆ ระหว่างเซสชันนี้)
- ✅ `clasp push` สำเร็จ — 15 ไฟล์ (รันผ่าน terminal จริงนอก Claude Code
  เพราะ Bash tool ไม่ใช่ TTY ทำให้ manifest confirmation prompt ของ `clasp`
  ข้ามไปเงียบๆ เสมอ — ถ้าเจอ "Skipping push." อีกในอนาคต ให้เปิด terminal
  จริงเองแทน ไม่ต้องใช้ `--force`)
- ✅ `appsscript.json` บน Apps Script online เช็คแล้วตรงกับ local ทุกตัวอักษร
- ❌ **ยังไม่ทดสอบผ่าน Test deployments**
- ❌ **ยังไม่ commit git**

---

## 3. งานแรกของแชทใหม่ — ทดสอบตาม checklist (จากแผน F.4 หัวข้อ 9)

1. เปิด Apps Script editor → **Deploy → Test deployments** → เปิด URL ทดสอบ
2. **เคส 1**: เลือก `001_Hor_Align` → `HOR-ORR-04` → alignment tab → กด
   "คำนวณ" — เช็ค dropdown+ปุ่ม disable ระหว่างรอ, สรุปผลถูกต้อง (25
   elements, ไม่พบ issues), 4 tab ผลลัพธ์ถูกต้อง, **ไม่มี** tab Issues
3. **เคส 2**: อัปโหลด `SettingOutTest_Part_2.csv` เป็น tab ใหม่ (label
   `PI1`-`PI11` ไม่มีขีด) → คำนวณ — เช็คว่า `normalizePiLabels_()` ทำงาน
   ถูกต้อง ไม่ error
4. **เคส 3**: กดคำนวณซ้ำ 2 ครั้งติด (alignment เดิม) — เช็คทับผลเดิมได้

ทดสอบผ่านครบแล้วค่อย commit (feat + docs แยกก้อนตามธรรมเนียมเดิม) แล้ว push

---

## 4. กฎเหล็กของโปรเจกต์ (ย่อ)

- **Plan-Review-Approve เสมอ** — Claude Code เขียนแผน/ทำงาน → Claude Chat
  ตรวจก่อน → อนุมัติถึงทำจริง ทีละ step ไม่ batch
- **ไฟล์เดียวกันมีอยู่ 2 ที่เสมอ**: repo (`reference/gsheet/*.gs`) กับ clasp
  folder (`D:\MyClasp_SMT_DEMO\*.js` flat) — ต้อง copy จาก repo ไปที่นั่นก่อน
  push เสมอ (`TestDrive.js` อยู่ที่ clasp folder เท่านั้น ไม่ track ใน git)
- **Commit message**: heredoc ผ่าน Git Bash เท่านั้น ใช้ **forward slash
  เสมอ** (`.git/smt_commit_msg.txt`) — เพิ่งแก้กฎนี้ให้ตรงความจริงใน F.3
  (เดิมเข้าใจผิดว่าต้องห้าม heredoc เพราะยุค bash tool เป็น PowerShell)
  ตรวจ `cat -A` ก่อน commit ทุกครั้ง
- **กด "Yes" ปกติ** สำหรับ: commit ผ่าน heredoc, `git status`/`git diff`,
  `clasp status`, session_logs append — **ตรวจทุกครั้งก่อนกด (ไม่ auto-allow
  แบบกว้าง)** สำหรับ: `git push`, `clasp push` — เคยเจอไฟล์เพี้ยนระหว่าง
  paste เข้าแชทหลายรอบใน F.3-F.4 (เนื้อหาไทยหาย, hash ขาด, บรรทัดตัดกลางคำ)
  แต่**ไฟล์จริงบนดิสก์ถูกต้องเสมอทุกครั้ง** — วิธีเช็คที่เชื่อถือได้คือ
  อัปโหลดไฟล์จริงเข้าแชท ไม่ใช่เชื่อ preview ที่ paste มา
- **เลิกใช้ BUNDLE_gsheet.md/BUNDLE_python_core.md** — แนบไฟล์จริงเฉพาะที่
  เกี่ยวข้องกับงานแทน (ดูหัวข้อ 1)

---

## 5. ข้อความเริ่มแชทใหม่

```
นี่คือ handoff สำหรับต่อ Session F.4 (แนบไฟล์ HANDOFF_CONTINUE_F4_20260729.md
พร้อม PROJECT_STATE.md, CLAUDE.md, DEPENDENCY_MAP.md, GS_Pipeline.gs,
GS_SheetExport.gs, TestDrive.js, Index.html) — โค้ด F.4 เขียน+ตรวจ+clasp push
เสร็จหมดแล้ว ยังไม่ได้ทดสอบผ่าน Test deployments และยังไม่ commit

งานแรกของแชทใหม่: ทดสอบตาม checklist ในหัวข้อ 3 ของ handoff แล้วค่อย commit
```
