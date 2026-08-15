# แผน: แก้ column-alias "STATION" + UI spinner ค้าง

**วันที่:** 2026-08-13
**สถานะ:** ร่างแผน ผ่านการทดสอบครบ (Python + Node สำหรับ GAS) รอ Claude Code implement ตาม Plan-Review-Approve

**อ้างอิง:** `session_logs/investigate_ui_spinner_station_alias_20260813.md`

## สรุปขอบเขต (3 ส่วน ตามที่ CK1024 approve ไว้)

1. เพิ่ม `'station': 'sta'` เข้า column-alias — ทั้ง Python (`table_splitter.py`)
   และ GAS (`reference/gsheet/GS_TableSplitter.gs`)
2. แก้ `onCalcFail()` ใน `reference/gsheet/Index.html` ให้เคลียร์/อัปเดต
   `calcStatus` (ไม่ใช่แค่ `showError()`)
3. (ทางเลือก) แก้ header cell ในชีต `HOR_SMT_AL1` จาก "STATION" เป็น "STA" —
   ไม่จำเป็นอีกต่อไปหลังข้อ 1 แก้แล้ว (ทั้งสองคำจะรู้จักเหมือนกัน) แต่ทำได้
   ถ้าอยากให้สอดคล้องกับ template อื่น

**หมายเหตุ:** `table_splitter.py`/`GS_TableSplitter.gs` **ไม่ใช่** protected
function — แก้ตรงได้เลย ไม่ต้องผ่านกระบวนการ Oracle correction exception

## Diff #1 — `src/smt/builders/table_splitter.py`

ทดสอบผ่านแล้ว: จำลอง header "STATION" จริง → ก่อนแก้ได้ `ValueError: could
not convert string to float: ''` (เพราะ 'station' ไม่ resolve) → หลังแก้
`drawing` ได้ค่าถูกต้องครบ ไม่มี error `pytest -q` เต็มชุด → **529 passed**
(528 เดิม + 1 ใหม่)

```diff
--- /home/claude/smt_repo/src/smt/builders/table_splitter.py	2026-08-07 11:27:57.317810397 +0000
+++ /home/claude/smt_repo_ui_fix/src/smt/builders/table_splitter.py	2026-08-13 13:29:29.866557202 +0000
@@ -20,6 +20,7 @@
 _COL_ALIASES: dict[str, str] = {
     'point':      'point',
     'sta':        'sta',
+    'station':    'sta',
     'chainage':   'sta',
     'n':          'northing',
     'northing':   'northing',
```

## Diff #2 — `tests/builders/test_table_splitter.py` (เทสใหม่ regression)

```diff
--- /home/claude/smt_repo/tests/builders/test_table_splitter.py	2026-08-07 11:27:57.324386058 +0000
+++ /home/claude/smt_repo_ui_fix/tests/builders/test_table_splitter.py	2026-08-13 13:30:23.625491312 +0000
@@ -129,3 +129,29 @@
         report = check_against_drawing(build_result.control, drawing, tolerance=0.1)
         max_gap = max(r['gap_m'] for r in report)
         assert max_gap < 0.08
+
+
+# ---------------------------------------------------------------------------
+# Test: column-alias header matching (session_logs/investigate_ui_spinner_station_alias_20260813.md)
+# ---------------------------------------------------------------------------
+
+class TestColumnAliases:
+
+    def test_station_header_recognized_as_sta(self):
+        # 'STATION' (full word) must resolve the same as 'STA' (abbreviation).
+        # Previously only 'sta'/'chainage' were recognized, so a sheet using
+        # the full word left every drawing row's station cell blank -> float('')
+        # raised (or, on the GAS side, parseFloat('') silently produced NaN
+        # that only surfaced much later as a confusing "station NaN" error).
+        rows = [
+            ['POINT', 'STATION', 'N', 'E'],
+            ['BP', '0', '1000', '2000'],
+            ['PC', '50', '1050', '2000'],
+            ['PT', '150', '1100', '2050'],
+            ['EP', '200', '1100', '2100'],
+        ]
+        vertex_rows, drawing = split_mixed_alignment_table(rows)
+        assert drawing == [
+            {'name': 'PC', 'sta': 50.0, 'n': 1050.0, 'e': 2000.0},
+            {'name': 'PT', 'sta': 150.0, 'n': 1100.0, 'e': 2050.0},
+        ]
```

## Diff #3 — `reference/gsheet/GS_TableSplitter.gs`

ทดสอบผ่านแล้วใน Node ด้วย header "STATION" เดียวกัน — ได้ผลตรงกับ Python
เป๊ะทุกค่า (`drawing`: PC sta=50, PT sta=150)

```diff
--- /home/claude/smt_repo/reference/gsheet/GS_TableSplitter.gs	2026-08-07 11:27:57.291573044 +0000
+++ /home/claude/ui_fix_gs/GS_TableSplitter.gs	2026-08-13 13:31:37.872840614 +0000
@@ -26,6 +26,7 @@
   var COL_ALIASES = {
     'point':      'point',
     'sta':        'sta',
+    'station':    'sta',
     'chainage':   'sta',
     'n':          'northing',
     'northing':   'northing',
```

## Diff #4 — `reference/gsheet/Index.html`

ไม่ได้รันทดสอบอัตโนมัติ (เป็น DOM manipulation ในเบราว์เซอร์ ทดสอบจริงได้
แค่ผ่าน live test) แต่เป็นการเพิ่ม 1 บรรทัดที่ตรงกับ pattern เดียวกับใน
`onCalcDone()` ที่ทำงานถูกต้องอยู่แล้วในไฟล์เดียวกัน ความเสี่ยงต่ำมาก

```diff
--- a/reference/gsheet/Index.html
+++ b/reference/gsheet/Index.html
@@ -391,6 +391,7 @@
       document.getElementById('tabSelect').disabled = false;
       document.getElementById('calcBtn').disabled = false;

+      document.getElementById('calcStatus').textContent = 'คำนวณไม่สำเร็จ';
       showError(err);
     }
```

## ขั้นตอนแนะนำสำหรับ Claude Code

1. apply diff #1+#2 (`table_splitter.py` + เทสใหม่) → โชว์ diff จริง →
   `pytest tests/builders/test_table_splitter.py -v` + `pytest -q` เต็มชุด
   (คาดหวัง 529 passed) → รอ approve
2. apply diff #3 (`reference/gsheet/GS_TableSplitter.gs`) → โชว์ diff จริง →
   รอ approve
3. apply diff #4 (`reference/gsheet/Index.html`) → โชว์ diff จริง → รอ approve
4. copy ทั้ง `GS_TableSplitter.gs` และ `Index.html` เข้า `D:\MyClasp_SMT_DEMO\`
   → `diff` ยืนยัน byte-identical (exit 0 ทั้งคู่)
5. commit + push เข้า git (heredoc + `cat -A` ตามเดิม)
6. `clasp push -f` เข้าเว็บแอปต้นแบบ (เช็ค `appsscript.json` manifest ก่อน
   เหมือนรอบที่แล้ว เผื่อมีอะไรเปลี่ยนอีก)
7. live test ซ้ำบน Test deployment — กด "คำนวณ" กับ `HOR_SMT_AL1`/`SMT_AL1`
   อีกครั้ง คาดว่าจะไม่มี warning "อยู่นอกแนวเส้นทาง" อีกแล้ว (เพราะ STATION
   ถูก resolve ถูกต้อง) และถ้าลอง error กรณีอื่น (เช่น เปิด tab ที่ไม่มีข้อมูล)
   `calcStatus` ควรอัปเดตข้อความแทนที่จะค้าง "กำลังคำนวณ..."
8. session_logs/latest.md append (เตรียมไฟล์ให้เหมือนเดิม)
