# แผนเต็ม: .gs sync สำหรับ #1, #2, #3 (Google Apps Script)

**วันที่:** 2026-08-10
**สถานะ:** ร่างแผน ผ่านการสืบสวน + ทดสอบ patch ครบใน Node (เทียบ Python จนตรงกันทุกตัวเลข) รอ Claude Code implement ตาม Plan-Review-Approve

**อ้างอิง:** `session_logs/investigate_gsheet_sync_scope_20260810.md`, `session_logs/review_src_smt_20260802.md` #1/#2/#3

---

## สรุปขอบเขต

| บั๊ก | ไฟล์ | สถานะก่อน sync |
|---|---|---|
| #1 singular-deflection guard | `reference/gsheet/GS_AlignmentBuilder.gs` | ยังไม่แก้ — ไม่มี guard เลย |
| #2 curve-overlap direction guard | `reference/gsheet/GS_AlignmentBuilder.gs` | ยังไม่แก้ — unsigned distance ล้วน |
| #3 orphan compound-sub-row guard | `reference/gsheet/GS_PiTableParser.gs` | ยังไม่แก้ — `flushPending_()` ไม่เคลียร์ `compoundArcs` |

**ยืนยันแล้วว่ากระทบเว็บแอปจริงที่ทีมงานใช้งานอยู่** (`D:\MyClasp_SMT_DEMO`, scriptId
`1nZHagNeQJL-uCjJe0Ux-pApWgS5loJuT0NfOdRMKhoXAb9gWDHfwNjPp`) — ไฟล์ที่ deploy จริง
ตรงกับ `reference/gsheet/*.gs` ใน git แบบ byte-for-byte (diff exit code 0) และ
`runFullPipeline()` เรียกไฟล์เหล่านี้ตรงๆ

## ⚠️ พบและแก้ document error จาก #1/#2 เดิม

`CLAUDE.md`/`docs/extensions.md` entry ของ #1 และ #2 เขียนไว้ว่า divergence อยู่ที่
`reference/AlignmentBuilder.gs` (top-level, ไม่มี `gsheet/`) — **ยืนยันแล้วว่าไฟล์นี้
เป็นไฟล์ตาย** (คอมมิตเดียวตั้งแต่สร้าง `65d9cdb`, ไม่มี EXT-001/EXT-003, ไม่ตรงกับไฟล์ที่
deploy จริงเลย) ไฟล์ที่ deploy จริงคือ `reference/gsheet/GS_AlignmentBuilder.gs`
(v2.0) — แผนนี้แก้ทั้งโค้ดและแก้คำอธิบายให้ชี้ไปไฟล์ที่ถูกต้อง

**ไม่ลบ/แก้ `reference/AlignmentBuilder.gs`** — เก็บไว้เป็นหลักฐานประวัติศาสตร์ v1.1 เฉยๆ

## ตรวจแล้วว่า `crossCheck()` (ใน `GS_AlignmentBuilder.gs`) เป็น dead code

มีบั๊ก pattern เดียวกับ #4 (silent skip, ไม่มีเพดานระยะ) แต่ยืนยันด้วย `grep`
ทั้งโฟลเดอร์ deploy จริงแล้วว่าไม่มีที่ไหนเรียกใช้ (`GS_CrossCheck.js` จาก Session E
มาแทนที่ไปแล้ว) — **ไม่รวมอยู่ในขอบเขต sync รอบนี้**

---

## Diff #1 — `reference/gsheet/GS_AlignmentBuilder.gs` (แก้ #1 + #2 พร้อมกัน)

ทดสอบผ่านแล้วใน Node เทียบ Python:
- Fix #1 (δ≈0 มี R): fallback เป็น angle point ถูกต้อง (เดิม: `sta`/`n`/`e` เป็น `null` เงียบๆ)
- Fix #1 (δ≈π): fallback ถูกต้องเช่นกัน
- Fix #2 (fixture Python จริงจาก `TestCurveOverlapDetection`): 2 issues ตรงเป๊ะ,
  `hasGeometricOverlap=true`, **station ตรงกับ Python ทุกทศนิยม** (77.124, 583.222,
  914.007, 1201.792, 1219.321)
- Regression (โค้งปกติ): ไม่ trigger guard เลยทั้งคู่
- **ข้อมูลจริง AL1 (`test_data/AL1_test_alignment_PI.csv`) ผ่านทั้ง pipeline:
  36 control points ตรงกับ Python ทุกจุดทุกทศนิยม**, `issues=[]`,
  `hasGeometricOverlap=true` ตรงกับ Python เป๊ะ (รวมถึง noise เดียวกันจากการปัดเศษ
  3 ตำแหน่งที่ Python เจอตอนพัฒนา #2 ด้วย)

```diff
--- /mnt/user-data/uploads/GS_AlignmentBuilder.js	2026-08-10 13:21:59.056398000 +0000
+++ /home/claude/gs_sync/sub/GS_AlignmentBuilder.gs	2026-08-10 13:39:10.119140535 +0000
@@ -44,6 +44,19 @@
 var GS_AlignmentBuilder = (function () {
   'use strict';
 
+  // Threshold for the delta≈π (180° reversal) branch of the singular-deflection
+  // guard (Oracle correction, session_logs/review_src_smt_20260802.md #1).
+  // Mirrors Python's _NEAR_PI_EPS (src/smt/builders/alignment_builder.py) --
+  // see that file's comment for the full derivation (Civil 3D rounding floor
+  // vs tightest real hairpin curves). FPMath.EPS covers the delta≈0 branch.
+  var NEAR_PI_EPS_ = 1e-4;   // ~20 arcsec from exact pi
+
+  // Tolerance for the curve-overlap direction guard (Oracle correction,
+  // session_logs/review_src_smt_20260802.md #2). Mirrors Python's
+  // TOL_METERS -- see that file's comment for the full derivation (real
+  // field-data noise floor from AL1_test_alignment_PI.csv / HOR_01N01.csv).
+  var TOL_METERS_ = 0.02;   // 2 cm
+
   // แตกโครงสร้างโค้งที่ PI ออกเป็นรายการ sub-element (kind, R, len, trans)
   // absD = มุมเลี้ยวรวม (รัศมีบวก), คืน {subs, issue}
   // EXT-003: มุมเลี้ยว spiral จริง (แทนสูตรเชิงเส้น Ls/(2R)) mirror
@@ -127,6 +140,7 @@
 
   function buildFromPI(vertices) {
     var els = [], control = [], issues = [];
+    var hasGeometricOverlap = false;
     var N = vertices.length;
     if (N < 2) {
       throw new Error(
@@ -148,6 +162,23 @@
       if (cs.issue) issues.push('PI#' + v + ': ' + cs.issue);
       var subs = cs.subs;
 
+      // FIX (Oracle correction, session_logs/review_src_smt_20260802.md #1,
+      // session_logs/plan_<TBD>.md): sin(delta)≈0 makes the 2x2 tangent-
+      // intersection solve below singular in two distinct cases -- mirrors
+      // build_alignment_from_pi (src/smt/builders/alignment_builder.py,
+      // commit 454b55d) line-for-line. See that file's comment for the full
+      // two-threshold rationale (delta≈0 removable vs delta≈π non-removable).
+      if (subs && subs.length && (
+        Math.abs(Math.sin(delta)) < FPMath.EPS ||
+        Math.abs(Math.PI - Math.abs(delta)) < NEAR_PI_EPS_
+      )) {
+        issues.push(
+          'PI#' + v + ': มุมเบี่ยง ' + FPMath.radToDeg(delta).toFixed(6) + '° ทำให้หาจุดเริ่มโค้งไม่ได้ ' +
+          '(sin(Δ)≈0 — เรียงเส้นตรงหรือหักกลับ 180°) ใช้ angle point (IP) แทนโค้งที่ระบุ'
+        );
+        subs = [];
+      }
+
       // EXTENSION: beyond oracle — angle point (no curve)
       // เกิดเมื่อ R หายหรือ R=0 (รวมถึง collinear PI ที่ delta=0)
       if (!subs || subs.length === 0) {
@@ -173,6 +204,29 @@
       // tangent: prev -> curveStart
       var tanLen = WCB.distance2D(prev.n, prev.e, curveStart.n, curveStart.e);
       var staCS = prev.sta + tanLen;
+
+      // FIX (Oracle correction, session_logs/review_src_smt_20260802.md #2,
+      // session_logs/plan_<TBD>.md): tanLen above is an unsigned distance
+      // (hypot) so a curve with too little tangent (overlapping the
+      // previous curve/BP) was never detected -- mirrors
+      // build_alignment_from_pi (src/smt/builders/alignment_builder.py,
+      // commit 39df582) line-for-line. prev and curveStart always lie on
+      // the same azIn line by construction, so this dot product is a true
+      // signed tangent-leg length. prev may be BP itself (v === 1).
+      var dnOv = curveStart.n - prev.n;
+      var deOv = curveStart.e - prev.e;
+      var tanLenSigned = dnOv * Math.cos(azIn) + deOv * Math.sin(azIn);
+      if (tanLenSigned < 0) hasGeometricOverlap = true;
+      if (tanLenSigned < -TOL_METERS_) {
+        var prevLabel = (v === 1) ? 'BP' : ('PI#' + (v - 1));
+        issues.push(
+          'PI#' + v + ': จุดเริ่มโค้ง (curve_start) อยู่หลังจุดจบของ ' + prevLabel + ' ' +
+          'ตามทิศทาง azimuth_in (' + FPMath.radToDeg(azIn).toFixed(4) + '°) — ' +
+          'โค้งซ้อนทับกัน (tan_len_signed = ' + tanLenSigned.toFixed(4) + ' m, ต้อง >= -' + TOL_METERS_.toFixed(2) + ' ม.) ' +
+          'ตรวจสอบ R/Ls หรือระยะห่างระหว่าง ' + prevLabel + ' และ PI#' + v
+        );
+      }
+
       els.push(GS_Alignment.makeElement('T', prev.sta, staCS, prev.n, prev.e, FPMath.radToDeg(azIn), 0));
       control.push({ name: nm.start, sta: staCS, n: curveStart.n, e: curveStart.e });
 
@@ -197,7 +251,7 @@
     els.push(GS_Alignment.makeElement('T', prev.sta, prev.sta + endLen, prev.n, prev.e, FPMath.radToDeg(azEnd), 0));
     control.push({ name: 'EP', sta: prev.sta + endLen, n: ep.n, e: ep.e });
 
-    return { elements: els, control: control, issues: issues };
+    return { elements: els, control: control, issues: issues, hasGeometricOverlap: hasGeometricOverlap };
   }
 
   function crossCheck(control, drawing, tol) {
```

## Diff #2 — `reference/gsheet/GS_PiTableParser.gs` (แก้ #3)

ทดสอบผ่านแล้วใน Node เทียบ Python:
- orphan sub-row ก่อน PI แรก → throw ถูกต้อง อ้างแถวที่ 3 ตรงกับ Python
- orphan sub-row หลัง EP → throw ถูกต้อง อ้างแถวที่ 5 ตรงกับ Python
- compound curve ที่ถูกต้อง → ยังทำงานปกติ ไม่กระทบ

```diff
--- /mnt/user-data/uploads/GS_PiTableParser.js	2026-08-10 13:22:16.585089000 +0000
+++ /home/claude/gs_sync/sub/GS_PiTableParser.gs	2026-08-10 13:40:20.633338074 +0000
@@ -99,9 +99,26 @@
     var pendingPiLabel = '';
     var pendingPiLine = 0;
     var compoundArcs = [];
+    var compoundArcsFirstLine = 0;
 
     function flushPending_() {
-      if (pendingPi === null) return;
+      if (pendingPi === null) {
+        // FIX (Oracle correction, session_logs/review_src_smt_20260802.md #3,
+        // session_logs/plan_<TBD>.md): mirrors parse_pi_table's
+        // _flush_pending (src/smt/builders/alignment_builder.py, commit
+        // 795f36b) line-for-line. A compound sub-row with no PI to attach
+        // to (before the first PI, or after EP) used to leak silently onto
+        // the next PI or vanish at EOF -- now raises instead.
+        if (compoundArcs.length) {
+          throw new Error(
+            'compound sub-row (แถวที่ ' + compoundArcsFirstLine + ') มีค่า RADIUS ' +
+            'แต่ไม่มี PI ก่อนหน้าให้ผูก (อยู่ก่อน PI ตัวแรก ก่อน BP, ' +
+            'หรืออยู่หลัง EP) ' +
+            'ตรวจสอบลำดับแถวในไฟล์ว่าไม่มีแถวตกหล่นหรือเรียงผิดที่'
+          );
+        }
+        return;
+      }
       var v;
       if (compoundArcs.length) {
         if (pendingPi.R !== undefined) {
@@ -132,6 +149,7 @@
         // compound sub-row — only meaningful when R is non-blank
         var rRaw = g(row, 'radius');
         if (!rRaw) continue;
+        if (!compoundArcs.length) compoundArcsFirstLine = lineNo;
         var arc = { R: toFloat_(rRaw) };
         var deltaRaw = g(row, 'delta');
         if (deltaRaw) arc.delta = toFloat_(deltaRaw);
```

---

## เอกสารที่ต้องแก้

### 1) `CLAUDE.md` — 2 บูลเล็ต (บรรทัด ~151, ~158)

**บูลเล็ต #1 (สร้างใหม่ทั้งบูลเล็ต ต่อท้ายเนื้อหาเดิม เปลี่ยนแค่ประโยคสุดท้าย):**

เดิม (บรรทัดสุดท้ายของบูลเล็ต):
```
docs/extensions.md entry "Oracle Correction — build_alignment_from_pi
Singular Deflection Guard", session_logs/plan_20260802_1904.md + addendum —
`reference/AlignmentBuilder.gs`/VBA ยังไม่ sync ตาม (known divergence)
```

แก้เป็น:
```
docs/extensions.md entry "Oracle Correction — build_alignment_from_pi
Singular Deflection Guard", session_logs/plan_20260802_1904.md + addendum —
sync ไปยัง `reference/gsheet/GS_AlignmentBuilder.gs` แล้วเมื่อ 2026-08-10
(ไฟล์ `reference/AlignmentBuilder.gs` เดิมที่อ้างถึงเป็นไฟล์ตาย v1.1 ไม่ใช่
ไฟล์ที่ deploy จริง — แก้คำอธิบายจุดนี้ด้วย) VBA ไม่มีพอร์ตฟังก์ชันนี้เลย
```

**บูลเล็ต #2:**

เดิม (บรรทัดสุดท้ายของบูลเล็ต):
```
Correction — build_alignment_from_pi Curve-Overlap Direction Guard" —
`reference/AlignmentBuilder.gs` ยังไม่ sync ตาม (known divergence)
```

แก้เป็น:
```
Correction — build_alignment_from_pi Curve-Overlap Direction Guard" —
sync ไปยัง `reference/gsheet/GS_AlignmentBuilder.gs` แล้วเมื่อ 2026-08-10
```

**บูลเล็ต #3 (parse_pi_table #3, บรรทัด ~159):** บรรทัดสุดท้ายที่พูดถึง `.gs` divergence
แก้จาก "ยังไม่ sync ตาม" เป็น "sync แล้วเมื่อ 2026-08-10"

### 2) `docs/extensions.md` — 3 ส่วน "สถานะ .gs/VBA — divergence ที่รู้ตัว ยังไม่ sync"

**ส่วนของ #1 (หัวข้อ "Oracle Correction — build_alignment_from_pi Singular Deflection Guard"):**

เปลี่ยนหัวข้อจาก `### สถานะ .gs/VBA — divergence ที่รู้ตัว ยังไม่ sync` เป็น
`### สถานะ .gs/VBA — synced 2026-08-10` แล้วแก้เนื้อหาทั้งย่อหน้าเป็น:
```
**แก้ไขคำอธิบายเดิม:** entry นี้เคยอ้างถึง `reference/AlignmentBuilder.gs`
(top-level) แต่ตรวจสอบระหว่างงาน sync (2026-08-10) พบว่าไฟล์นั้นเป็นไฟล์ตาย
v1.1 (คอมมิตเดียวตั้งแต่สร้าง ไม่มี EXT-001/EXT-003) ไม่ใช่ไฟล์ที่ deploy จริง
— ไฟล์ที่ deploy จริงคือ `reference/gsheet/GS_AlignmentBuilder.gs` ยืนยันแล้ว
ว่ามี defect เดียวกันเป๊ะ (ไม่มี guard สำหรับ sin(delta)≈0 เลย) ตอนนี้ sync แล้ว
— ทดสอบผ่าน Node เทียบ Python จนตรงกันทุกตัวเลข (ดู commit sync ที่เกี่ยวข้อง)
VBA: ไม่มีพอร์ต `build_alignment_from_pi` เลย (ตาราง VBA Engine map ใน
CLAUDE.md ไม่มี AlignmentBuilder.gs อยู่) — ไม่มี divergence ต้อง track
```

**ส่วนของ #2 (หัวข้อ "Oracle Correction — build_alignment_from_pi Curve-Overlap Direction Guard"):**

หัวข้อเปลี่ยนเป็น `### สถานะ .gs/VBA — synced 2026-08-10` เนื้อหาบูลเล็ตแรก
(`reference/AlignmentBuilder.gs:122-123`) แก้ path เป็น
`reference/gsheet/GS_AlignmentBuilder.gs` และเปลี่ยน "ยังไม่แก้ตามในรอบนี้" เป็น
"sync แล้วเมื่อ 2026-08-10 — ทดสอบผ่าน Node เทียบ Python จนตรงกันทุกตัวเลข
(รวมถึงข้อมูลจริง AL1 ที่พบ tan_len_signed ติดลบเล็กน้อยจาก rounding เหมือนกับที่
Python เจอตอนพัฒนา #2)" บูลเล็ตที่สอง (`:145` EP-tangent, ปิดแล้วว่าไม่ใช่บั๊ก)
และบูลเล็ต VBA ปล่อยไว้เหมือนเดิม ไม่ต้องแก้

**ส่วนของ #3 (หัวข้อ "Oracle Correction — parse_pi_table Orphan Compound-Sub-Row Guard"):**

หัวข้อเปลี่ยนเป็น `### สถานะ .gs/VBA — synced 2026-08-10` บูลเล็ต
`reference/gsheet/GS_PiTableParser.gs` แก้ "ยังไม่แก้ตามในรอบนี้" เป็น
"sync แล้วเมื่อ 2026-08-10 — ทดสอบผ่าน Node เทียบ Python จนตรงกันทุกตัวเลข
(รวมถึงเลขบรรทัดในข้อความ error)" บูลเล็ต VBA ปล่อยไว้เหมือนเดิม

---

## session_logs/latest.md — entry ใหม่

จะเตรียมเนื้อหาให้แยกเป็นไฟล์ append-content เหมือนเดิม (ไฟล์ใหญ่ ต้อง append เท่านั้น)
หลังโค้ด+เอกสารผ่านการ approve แล้ว

---

## ขั้นตอนแนะนำสำหรับ Claude Code (ทีละสเต็ป ตามกฎ ไม่ batch)

1. apply diff #1 (`reference/gsheet/GS_AlignmentBuilder.gs`) → โชว์ diff จริง →
   รอ approve (ไฟล์นี้มีโค้ด+Thai ยาว แนะนำใช้วิธี apply-แล้ว-mechanical-grep-check
   แบบที่ใช้ตอนท้าย #4 แทนการพิมพ์ diff เต็มซ้ำ)
2. apply diff #2 (`reference/gsheet/GS_PiTableParser.gs`) → เหมือนข้อ 1
3. **verify ในเครื่องจริงด้วย Node** — รันคำสั่งเทียบผลเหมือนที่ Claude Chat ทดสอบผ่านมาแล้ว
   (จะให้คำสั่ง Node ที่ต้องรันในสเต็ปถัดไปหลัง diff 1-2 ผ่าน)
4. **copy ไฟล์ที่แก้แล้วเข้า `D:\MyClasp_SMT_DEMO\`** (`GS_AlignmentBuilder.js`,
   `GS_PiTableParser.js`) — ยังไม่ `clasp push`
5. **verify ซ้ำในโฟลเดอร์ clasp** ด้วย Node คำสั่งเดียวกัน (ให้แน่ใจว่า copy ไม่เพี้ยน)
6. แก้ `CLAUDE.md` (3 บูลเล็ต) → โชว์ diff จริง → รอ approve
7. แก้ `docs/extensions.md` (3 ส่วน) → โชว์ diff จริง → รอ approve
8. `session_logs/latest.md` append (heredoc) → รอ approve
9. commit message ผ่าน `.git/smt_commit_msg.txt` + `cat -A` เช็ค → commit → โชว์
   `git log -3 --oneline`
10. push → ยืนยัน raw `git log` ทั้ง local/origin ตรงกัน
11. **`clasp push` เข้า `MyClasp_SMT_DEMO`** — ขั้นตอนแยกต่างหาก ขอ approve เดี่ยวๆ
    ก่อนทำ (กระทบเว็บแอปจริงทันที) → ยืนยันด้วย `clasp status`/`clasp deployments`
12. **live test บนเว็บแอปจริง** — แนะนำให้ CK1024 ลองรันจริงบน Test deployment
    ก่อน promote เป็น production deployment ถาวร (ตามที่เคยทำใน Session F.6)
