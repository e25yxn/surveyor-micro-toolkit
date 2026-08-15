# แผนแก้บั๊ก #4: check_against_drawing — silent skip + ไม่มีเพดานระยะ
# + adapter ใหม่: normalize_ip_names / add_pcc_control_points

**วันที่:** 2026-08-09
**สถานะ:** ร่างแผน ผ่านการวิเคราะห์ + dry-run ครบแล้ว (รวม real-data validation กับ AL1) รอ Claude Code implement ตาม Plan-Review-Approve

## บั๊ก (อ้างอิง session_logs/review_src_smt_20260802.md #4)

`check_against_drawing` มี 2 ไฟล์ (`src/smt/builders/alignment_builder.py:548`,
`src/smt/builders/vertical_builder.py:164`) — ทั้งคู่มีบั๊กเดียวกัน:

1. drawing point ที่ชื่อไม่ match control point ใดเลย → `best is None` → `continue`
   **เงียบ ไม่มีแถวในรายงานเลย**
2. การจับคู่ closest-by-station **ไม่มีเพดานระยะ** — จุดที่ห่างจาก control ที่ใกล้สุด
   เป็นร้อย/พันเมตร ก็ยังถูกจับคู่แล้วรายงาน FAIL ที่ชวนสับสน แทนที่จะบอกว่า "ไม่มีคู่"

## เงื่อนไข Oracle correction exception — กรณีนี้ต่างจาก #1-#3

เช็คแล้วพบว่า `check_against_drawing` **ไม่มีพอร์ตใน `.gs`/VBA เลยสักที่**
(`grep` ทั้ง repo ไม่เจอ) — ฟังก์ชันที่ `GS_CrossCheck.gs::checkPoints()` mirror จริง
คือ `check.py::check_horizontal()` (คนละฟังก์ชัน คนละอัลกอริทึม ไม่มีบั๊กนี้เลย
เพราะคำนวณตำแหน่ง ณ สถานีที่ระบุโดยตรง ไม่ค้นหาจุดใกล้สุด)

**สรุป:** เงื่อนไขข้อ (1) ("พิสูจน์ว่า oracle มี defect เดียวกัน") เป็น N/A ในความหมาย
ที่ปลอดภัยกว่า #2/#3 (ไม่ใช่แค่ VBA ไม่มีพอร์ต แต่ **ทั้ง GAS และ VBA ไม่มีพอร์ตเลย**) —
ไม่มีความเสี่ยงขัดกับพฤติกรรมที่ oracle เคย verify ไว้ เพราะไม่มี oracle ให้ขัดตั้งแต่แรก
ยังต้องผ่านเงื่อนไขที่เหลือ (proof เชิงตรรกะ, เทส, เอกสาร, tracking) เหมือนเดิม

## ขอบเขต — core fix

แก้ 2 จุดในฟังก์ชันเดียวกัน ทำกับทั้ง 2 ไฟล์:
1. แทนที่ `if best is None: continue` ด้วยการ append แถว no-match ที่มี schema
   เดียวกับแถวปกติทุกประการ (`note` เป็น key เสมอทุกแถว — ปกติ `''`, ไม่พบ/ไกลเกิน
   เป็นข้อความอธิบาย) กัน `KeyError` ฝั่งโค้ดที่เอา report ไปใช้ต่อ
2. เพิ่มพารามิเตอร์ `max_sta_distance: float | None = 10.0` — ถ้าจุดใกล้สุดยังห่าง
   เกินนี้ ถือเป็น "ไม่พบ" เหมือนกัน (note ต่างข้อความ) แทนรายงาน FAIL ที่สับสน
   **default 10.0m** (ตาม CK1024: ความคลาดเคลื่อนหน้างานจริงไม่เกินไม่กี่เมตร
   ระยะระหว่างจุดจริงในไฟล์อยู่หลักร้อย-พันเมตร — 10m แยกกรณีจริงจาก
   typo/ป้ายชื่อผิดที่ไปจับจุดไกลๆ ได้ชัดเจน) — `None` ปิดเพดานได้ (คืนพฤติกรรมเดิม)

## ขอบเขต — adapter ใหม่ 2 ตัว (ใน check.py, แยกจาก core fix)

พบระหว่าง validate กับข้อมูลจริง (`AL1_test_alignment_drawing.csv`): 33% ของแถว
(15/45) เป็น no-match — 11 แถว (PI1-PI11) ถูกต้องอยู่แล้ว (PI คือจุดตัดแทนเจนต์
ไม่ใช่จุดบนเส้นทางจริง ไม่ควรมี control point ให้จับคู่) แต่ 4 แถว (IP1, IP2,
PCC×2) มีจุดจริงตรงตำแหน่งเป๊ะใน control แค่ชื่อไม่ตรง convention:

- **normalize_ip_names(drawing)** — ตัดเลขออกจากชื่อ `IP<เลข>` (`IP1`/`IP-1`/
  `IP-01`/`IP-001`/`IP 1` ทุกแบบ) → `IP` เปล่า ให้ตรงกับชื่อที่ control ใช้จริง
  ไม่แตะ `PI*` เลย (ถูกต้องอยู่แล้วที่ไม่ต้อง match — เข้าเงื่อนไข "แจ้ง error
  ให้ผู้ใช้ไปเช็คเอง" ตามที่ CK1024 ต้องการ ไม่ใช่ auto-fix แบบเดา)
- **add_pcc_control_points(control)** — หา `PT` ตามด้วย `PC` ทันทีที่ station
  ห่างกัน ≤ 0.001m (ยืนยันจากข้อมูลจริง: 2 คู่ในไฟล์ AL1 ห่างกัน 0.0004-0.001m)
  แล้วสร้างจุด control สังเคราะห์ชื่อ `PCC` ที่ midpoint เพิ่มเข้า list

**ไม่เข้าเงื่อนไข Oracle correction exception เลย** — เป็นฟังก์ชันใหม่ล้วนๆ
ไม่แตะ `check_against_drawing`/`build_alignment_from_pi` แม้แต่บรรทัดเดียว
ตรงตามกฎ adapter มาตรฐานของโปรเจกต์อยู่แล้ว

CK1024 ยืนยันแล้ว (ทดสอบจริงกับไฟล์ที่ไม่มีเลขกำกับด้วย): **ใส่เลขต่อท้าย
(`PI1`-`PI11`, `IP1`/`IP2`) ในไฟล์จริงได้ตามสบายเพื่อความสะดวกในการไล่หา**
ผลลัพธ์การตรวจจะออกมาเหมือนกันไม่ว่าจะมีเลขกำกับหรือไม่

## Real-data validation (AL1_test_alignment_drawing.csv, 45 แถว)

```
ก่อน fix:  30 matched, 15 no-match (ซ่อนเงียบทั้งหมด — ไม่มีแถวในรายงานเลย)
core fix เท่านั้น (ไม่มี adapter): 30 matched, 15 no-match (โผล่ชัดเจนในรายงานแล้ว)
core fix + adapter ทั้ง 2: 34 matched, 11 no-match (เหลือแค่ PI1-PI11 ที่ถูกต้อง)
```
gap ของ 4 จุดที่ adapter ทำให้ match ได้ใหม่: 0.0 - 0.0008m (ยืนยันเป็นจุดเดียวกันจริง)
ทดสอบ default 10m เพดานแล้วว่า**ไม่บล็อกจุดที่ควร match จริงแม้แต่จุดเดียว**ในข้อมูลนี้

## Diff ที่แนะนำ (ทดสอบผ่านแล้วครบใน sandbox — full pytest 528 passed)

### 1) src/smt/builders/alignment_builder.py

```diff
diff --git a/src/smt/builders/alignment_builder.py b/src/smt/builders/alignment_builder.py
index abdd095..4af92a6 100644
--- a/src/smt/builders/alignment_builder.py
+++ b/src/smt/builders/alignment_builder.py
@@ -549,6 +549,7 @@ def check_against_drawing(
     control: list[ControlPoint],
     drawing: list[dict[str, Any]],
     tolerance: float = 0.05,
+    max_sta_distance: float | None = 10.0,
 ) -> list[dict[str, Any]]:
     """Cross-check computed control points against drawn / surveyed coordinates.
 
@@ -556,9 +557,31 @@ def check_against_drawing(
     (filtered by name when drawing entry has a non-empty 'name' key), then
     computes the 2-D spatial gap.
 
+    FIX (Oracle correction, session_logs/review_src_smt_20260802.md #4,
+    session_logs/plan_<TBD>.md): check_against_drawing has no port in
+    reference/gsheet/ or reference/vba/ at all -- the function those mirror
+    is check.py::check_horizontal(), a different algorithm (evaluates the
+    alignment directly at the drawing station instead of searching a control
+    list). Condition (1) of the Oracle correction exception is therefore N/A
+    here: there is no oracle implementation of this specific matching
+    algorithm to diverge from. Previously a drawing point with no matching
+    name (best is None) was silently dropped with `continue`, and
+    closest-by-station matching had no distance ceiling, so a point far from
+    every control point still got matched and reported as a confusing FAIL.
+    Both are now reported as an explicit row (ok=False, note explains why)
+    instead of vanishing or misleadingly failing.
+
     drawing entries: {'name' (optional), 'sta', 'n', 'e'}.
-    Returns list of dicts: {name, sta_calc, sta_draw, gap_m, ok}.
-    ok is True when gap_m ≤ tolerance.
+    Returns list of dicts: {name, sta_calc, sta_draw, gap_m, ok, note}.
+    ok is True when gap_m ≤ tolerance. sta_calc/gap_m are None and ok is
+    False when no matching control point was found (name mismatch, or the
+    closest candidate exceeds max_sta_distance when that is set); note then
+    explains why. note is '' for a normal matched row.
+    max_sta_distance defaults to 10.0m (typical field/setting-out tolerance
+    is at most a few metres; a genuine match should never be this far off by
+    station -- 10m safely separates real deviations from name typos/mismatches
+    that would otherwise land on an unrelated control point far away). Pass
+    None to disable the ceiling entirely (restores pre-fix matching).
     """
     report: list[dict[str, Any]] = []
     for d in drawing:
@@ -574,6 +597,27 @@ def check_against_drawing(
                 best_d = dist
                 best = c
         if best is None:
+            report.append({
+                'name':     d_name,
+                'sta_calc': None,
+                'sta_draw': d_sta,
+                'gap_m':    None,
+                'ok':       False,
+                'note':     'ไม่พบจุดควบคุมที่ชื่อตรงกัน',
+            })
+            continue
+        if max_sta_distance is not None and best_d > max_sta_distance:
+            report.append({
+                'name':     d_name or best.name,
+                'sta_calc': None,
+                'sta_draw': d_sta,
+                'gap_m':    None,
+                'ok':       False,
+                'note': (
+                    f'จุดควบคุมที่ใกล้สุด ({best.name}) ห่างตามสถานี '
+                    f'{best_d:.3f} ม. เกินเพดาน {max_sta_distance:.3f} ม.'
+                ),
+            })
             continue
         gap = math.hypot(best.n - float(d['n']), best.e - float(d['e']))
         report.append({
@@ -582,5 +626,6 @@ def check_against_drawing(
             'sta_draw': d_sta,
             'gap_m':    gap,
             'ok':       gap <= tolerance,
+            'note':     '',
         })
     return report
```

### 2) src/smt/builders/vertical_builder.py

```diff
diff --git a/src/smt/builders/vertical_builder.py b/src/smt/builders/vertical_builder.py
index 3b55f0c..b63c7b8 100644
--- a/src/smt/builders/vertical_builder.py
+++ b/src/smt/builders/vertical_builder.py
@@ -166,6 +166,7 @@ def check_against_drawing(
     drawing: list[dict[str, Any]],
     tolerance_sta: float = 0.01,
     tolerance_elev: float = 0.005,
+    max_sta_distance: float | None = 10.0,
 ) -> list[dict[str, Any]]:
     """Cross-check computed control points against drawing / survey values.
 
@@ -173,10 +174,21 @@ def check_against_drawing(
     (filtered by name when drawing entry has a non-empty 'name' key), then
     computes station and elevation deviations.
 
+    FIX (Oracle correction, session_logs/review_src_smt_20260802.md #4,
+    session_logs/plan_<TBD>.md): same defect and same justification as the
+    horizontal check_against_drawing in alignment_builder.py -- see that
+    docstring. No reference/gsheet or reference/vba port of this specific
+    matching algorithm exists, so condition (1) of the Oracle correction
+    exception is N/A here.
+
     drawing entries: {'name' (optional), 'sta', 'elev'}.
-    Returns list of dicts: {name, sta, d_sta, d_elev, ok}.
+    Returns list of dicts: {name, sta, d_sta, d_elev, ok, note}.
     d_sta and d_elev are absolute differences (always ≥ 0).
     ok is True when d_sta ≤ tolerance_sta and d_elev ≤ tolerance_elev.
+    sta/d_sta/d_elev are None and ok is False when no matching control point
+    was found; note then explains why. note is '' for a normal matched row.
+    max_sta_distance defaults to 10.0m (see alignment_builder.check_against_drawing
+    for the full rationale). Pass None to disable the ceiling entirely.
     """
     report: list[dict[str, Any]] = []
     for d in drawing:
@@ -192,6 +204,27 @@ def check_against_drawing(
                 best_dist = dist
                 best = c
         if best is None:
+            report.append({
+                'name':   d_name,
+                'sta':    None,
+                'd_sta':  None,
+                'd_elev': None,
+                'ok':     False,
+                'note':   'ไม่พบจุดควบคุมที่ชื่อตรงกัน',
+            })
+            continue
+        if max_sta_distance is not None and best_dist > max_sta_distance:
+            report.append({
+                'name':   d_name or best.name,
+                'sta':    None,
+                'd_sta':  None,
+                'd_elev': None,
+                'ok':     False,
+                'note': (
+                    f'จุดควบคุมที่ใกล้สุด ({best.name}) ห่างตามสถานี '
+                    f'{best_dist:.3f} ม. เกินเพดาน {max_sta_distance:.3f} ม.'
+                ),
+            })
             continue
         d_sta_diff = abs(best.sta - d_sta)
         d_elev_diff = abs(best.elevation - float(d['elev']))
@@ -201,5 +234,6 @@ def check_against_drawing(
             'd_sta': d_sta_diff,
             'd_elev': d_elev_diff,
             'ok': d_sta_diff <= tolerance_sta and d_elev_diff <= tolerance_elev,
+            'note': '',
         })
     return report
```

### 3) src/smt/check.py (ฟังก์ชันใหม่ 2 ตัว)

```diff
diff --git a/src/smt/check.py b/src/smt/check.py
index a5181e2..a4cd043 100644
--- a/src/smt/check.py
+++ b/src/smt/check.py
@@ -19,10 +19,12 @@ Depends on: alignment, vertical.
 from __future__ import annotations
 
 import math
+import re
 from typing import Any, NamedTuple
 
 from . import alignment as al
 from . import vertical as vt
+from .builders.alignment_builder import ControlPoint
 
 # ---------------------------------------------------------------------------
 # Result types
@@ -215,3 +217,66 @@ def check_vertical(
             is_ok=abs(delta_elevation) <= tol,
         ))
     return results
+
+
+# ---------------------------------------------------------------------------
+# check_against_drawing naming adapters (session_logs/review_src_smt_20260802.md
+# #4 follow-up) - AL1_test_alignment_drawing.csv uses numbered angle-point
+# labels (IP1, IP2, ...) and a single 'PCC' label for a compound-curve
+# junction, neither of which appears in build_alignment_from_pi's control
+# output by that exact name (control uses bare 'IP', and a coincident PT+PC
+# pair rather than 'PCC'). These are adapters in front of
+# check_against_drawing, per the standing protected-function rule - neither
+# check_against_drawing nor build_alignment_from_pi is modified.
+# ---------------------------------------------------------------------------
+
+_IP_NUMBERED_RE = re.compile(r'^IP[-\s]?\d+$')
+
+
+def normalize_ip_names(drawing: list[dict[str, Any]]) -> list[dict[str, Any]]:
+    """Rename numbered angle-point labels (IP1, IP2, ...) to the bare 'IP'
+    used by build_alignment_from_pi's control output, so check_against_drawing
+    can match them by name.
+
+    Only entries whose 'name' matches IP<number> (optionally with a space or
+    hyphen before the number) are renamed; everything else, including a
+    drawing entry already named plain 'IP', passes through unchanged.
+    Returns a new list - the input is not mutated.
+    """
+    out: list[dict[str, Any]] = []
+    for d in drawing:
+        name = str(d.get('name') or '').strip()
+        if _IP_NUMBERED_RE.match(name):
+            d = {**d, 'name': 'IP'}
+        out.append(d)
+    return out
+
+
+def add_pcc_control_points(
+    control: list[ControlPoint],
+    sta_tolerance: float = 0.01,
+) -> list[ControlPoint]:
+    """Add a synthetic 'PCC' control point wherever a PT is immediately
+    followed by a PC at (essentially) the same station - the point of
+    compound curve, where two circular arcs in a compound-curve group meet.
+
+    Coordinates of the synthetic PCC point are the midpoint of the
+    coincident PT/PC pair. sta_tolerance (default 0.01 m) bounds how close
+    the pair's stations must be to be treated as coincident, so a genuine
+    PT followed much later by an unrelated PC's is left alone. Returns a
+    new list (original entries unchanged, PCC entries appended) - the input
+    is not mutated.
+    """
+    out: list[ControlPoint] = list(control)
+    new_points: list[ControlPoint] = []
+    for i in range(len(control) - 1):
+        a, b = control[i], control[i + 1]
+        if a.name == 'PT' and b.name == 'PC' and abs(a.sta - b.sta) <= sta_tolerance:
+            new_points.append(ControlPoint(
+                name='PCC',
+                sta=(a.sta + b.sta) / 2,
+                n=(a.n + b.n) / 2,
+                e=(a.e + b.e) / 2,
+            ))
+    out.extend(new_points)
+    return out
```

### 4) tests/builders/test_alignment_builder.py

```diff
diff --git a/tests/builders/test_alignment_builder.py b/tests/builders/test_alignment_builder.py
index fb6f389..d4e0d07 100644
--- a/tests/builders/test_alignment_builder.py
+++ b/tests/builders/test_alignment_builder.py
@@ -876,22 +876,81 @@ class TestDefensiveBuilder:
         assert [el.type for el in r1.elements] == [el.type for el in r2.elements]
         assert r1.issues == r2.issues == []
 
-    def test_check_against_drawing_empty_control_gives_empty_report(self):
-        # No control points → every drawing entry has best=None → skipped → []
+    def test_check_against_drawing_empty_control_reports_no_match_row(self):
+        # Regression test for review finding #4 (session_logs/review_src_smt_20260802.md).
+        # No control points -> every drawing entry has best=None -> now reported
+        # as an explicit no-match row instead of vanishing silently.
         drawing = [{'name': 'PC', 'sta': 100.0, 'n': 0.0, 'e': 0.0}]
         report = ab.check_against_drawing([], drawing)
-        assert report == []
-
-    def test_check_against_drawing_unknown_name_is_skipped(self):
-        # 'XYZ' does not match any control name → entry skipped, only 'PC' reported
+        assert len(report) == 1
+        row = report[0]
+        assert row['ok'] is False
+        assert row['sta_calc'] is None
+        assert row['gap_m'] is None
+        assert row['note'] != ''
+
+    def test_check_against_drawing_unknown_name_reports_no_match_row(self):
+        # 'XYZ' matches no control name -> reported as an explicit no-match
+        # row (not skipped); 'PC' still matches and reports normally.
         ctrl = [ab.ControlPoint(name='PC', sta=100.0, n=10.0, e=0.0)]
         drawing = [
             {'name': 'PC',  'sta': 100.0, 'n': 10.0, 'e': 0.0},
             {'name': 'XYZ', 'sta': 100.0, 'n': 10.0, 'e': 0.0},
         ]
         report = ab.check_against_drawing(ctrl, drawing)
-        assert len(report) == 1
+        assert len(report) == 2
         assert report[0]['name'] == 'PC'
+        assert report[0]['ok'] is True
+        assert report[0]['note'] == ''
+        assert report[1]['name'] == 'XYZ'
+        assert report[1]['ok'] is False
+        assert report[1]['sta_calc'] is None
+        assert report[1]['note'] != ''
+
+    def test_check_against_drawing_max_sta_distance_rejects_far_match(self):
+        # Closest-by-station candidate is farther than max_sta_distance ->
+        # treated as no-match instead of a confusing distant FAIL.
+        ctrl = [
+            ab.ControlPoint(name='BP', sta=0.0,   n=1000.0, e=2000.0),
+            ab.ControlPoint(name='EP', sta=600.0, n=1600.0, e=2000.0),
+        ]
+        drawing = [{'name': '', 'sta': 300.0, 'n': 1300.0, 'e': 2050.0}]
+        report = ab.check_against_drawing(ctrl, drawing, max_sta_distance=50.0)
+        assert len(report) == 1
+        assert report[0]['ok'] is False
+        assert report[0]['gap_m'] is None
+        assert report[0]['note'] != ''
+
+    def test_check_against_drawing_max_sta_distance_boundary_is_inclusive(self):
+        # Distance exactly equal to max_sta_distance still counts as matched.
+        ctrl = [ab.ControlPoint(name='PC', sta=100.0, n=0.0, e=0.0)]
+        drawing = [{'name': '', 'sta': 150.0, 'n': 0.0, 'e': 0.0}]  # 50m away
+        report = ab.check_against_drawing(ctrl, drawing, max_sta_distance=50.0)
+        assert len(report) == 1
+        assert report[0]['sta_calc'] == 100.0
+        assert report[0]['note'] == ''
+
+    def test_check_against_drawing_default_ceiling_rejects_far_match(self):
+        # max_sta_distance defaults to 10.0m -- a far-away point is rejected
+        # even without the caller passing anything explicitly.
+        ctrl = [ab.ControlPoint(name='BP', sta=0.0, n=1000.0, e=2000.0)]
+        drawing = [{'name': '', 'sta': 300.0, 'n': 1300.0, 'e': 2050.0}]
+        report = ab.check_against_drawing(ctrl, drawing)
+        assert len(report) == 1
+        assert report[0]['sta_calc'] is None
+        assert report[0]['ok'] is False
+        assert report[0]['note'] != ''
+
+    def test_check_against_drawing_max_sta_distance_none_disables_ceiling(self):
+        # Explicitly passing None restores pre-fix matching (no ceiling) -
+        # still matches a far-away point, only the schema (note key) is new.
+        ctrl = [ab.ControlPoint(name='BP', sta=0.0, n=1000.0, e=2000.0)]
+        drawing = [{'name': '', 'sta': 300.0, 'n': 1300.0, 'e': 2050.0}]
+        report = ab.check_against_drawing(ctrl, drawing, max_sta_distance=None)
+        assert len(report) == 1
+        assert report[0]['sta_calc'] == 0.0
+        assert report[0]['ok'] is False   # gap far exceeds tolerance
+        assert report[0]['note'] == ''    # matched, just failed tolerance - not a "no match"
 
 
 # ---------------------------------------------------------------------------
```

### 5) tests/builders/test_vertical_builder.py

```diff
diff --git a/tests/builders/test_vertical_builder.py b/tests/builders/test_vertical_builder.py
index 0fa7251..abb4334 100644
--- a/tests/builders/test_vertical_builder.py
+++ b/tests/builders/test_vertical_builder.py
@@ -156,7 +156,8 @@ def test_check_against_drawing_fail_on_large_error(result: vb.VerticalBuildResul
 def test_check_against_drawing_report_fields(result: vb.VerticalBuildResult) -> None:
     drawing = [{'name': 'BVP', 'sta': 0, 'elev': 100}]
     report = vb.check_against_drawing(result.control, drawing)
-    assert set(report[0].keys()) == {'name', 'sta', 'd_sta', 'd_elev', 'ok'}
+    assert set(report[0].keys()) == {'name', 'sta', 'd_sta', 'd_elev', 'ok', 'note'}
+    assert report[0]['note'] == ''
 
 
 # ---------------------------------------------------------------------------
@@ -241,12 +242,28 @@ class TestDefensiveVerticalBuilder:
         report = vb.check_against_drawing(result.control, [])
         assert report == []
 
-    def test_check_against_drawing_unknown_name_is_skipped(self, result) -> None:
-        # 'XYZ' matches no control name → entry skipped, only 'BVP' reported
+    def test_check_against_drawing_unknown_name_reports_no_match_row(self, result) -> None:
+        # Regression test for review finding #4 (session_logs/review_src_smt_20260802.md).
+        # 'XYZ' matches no control name -> reported as an explicit no-match
+        # row instead of vanishing; 'BVP' still matches and reports normally.
         drawing = [
             {'name': 'BVP', 'sta': 0,    'elev': 100},
             {'name': 'XYZ', 'sta': 0,    'elev': 100},
         ]
         report = vb.check_against_drawing(result.control, drawing)
-        assert len(report) == 1
+        assert len(report) == 2
         assert report[0]['name'] == 'BVP'
+        assert report[0]['ok'] is True
+        assert report[0]['note'] == ''
+        assert report[1]['name'] == 'XYZ'
+        assert report[1]['ok'] is False
+        assert report[1]['sta'] is None
+        assert report[1]['note'] != ''
+
+    def test_check_against_drawing_max_sta_distance_rejects_far_match(self, result) -> None:
+        drawing = [{'name': '', 'sta': 2500.0, 'elev': 102.0}]
+        report = vb.check_against_drawing(result.control, drawing, max_sta_distance=50.0)
+        assert len(report) == 1
+        assert report[0]['ok'] is False
+        assert report[0]['d_sta'] is None
+        assert report[0]['note'] != ''
```

### 6) tests/test_check.py

```diff
diff --git a/tests/test_check.py b/tests/test_check.py
index a211fdd..22460a5 100644
--- a/tests/test_check.py
+++ b/tests/test_check.py
@@ -25,6 +25,7 @@ import pytest
 from smt import alignment as al
 from smt import vertical as vt
 from smt import check as ck
+from smt.builders.alignment_builder import ControlPoint
 
 _GOLDEN = Path(__file__).parent / 'golden' / 'tables.json'
 
@@ -226,3 +227,67 @@ class TestBulkCrossCheck:
         fp = [{'name': 'FAR', 'n': 1000.0, 'e': 1000.0, 'z': 85.0, 'disc': 0.0}]
         with pytest.raises(ValueError):
             ck.bulk_cross_check(tangent_elements, fp)
+
+
+# ---------------------------------------------------------------------------
+# normalize_ip_names / add_pcc_control_points (session_logs/review_src_smt_20260802.md
+# #4 follow-up adapters)
+# ---------------------------------------------------------------------------
+
+def test_normalize_ip_names_strips_number() -> None:
+    drawing = [
+        {'name': 'IP1', 'sta': 100.0, 'n': 0.0, 'e': 0.0},
+        {'name': 'IP2', 'sta': 200.0, 'n': 0.0, 'e': 0.0},
+        {'name': 'IP10', 'sta': 300.0, 'n': 0.0, 'e': 0.0},
+    ]
+    out = ck.normalize_ip_names(drawing)
+    assert [d['name'] for d in out] == ['IP', 'IP', 'IP']
+
+
+def test_normalize_ip_names_leaves_others_unchanged() -> None:
+    drawing = [
+        {'name': 'PC', 'sta': 100.0, 'n': 0.0, 'e': 0.0},
+        {'name': 'IP', 'sta': 200.0, 'n': 0.0, 'e': 0.0},   # already bare
+        {'name': 'PI1', 'sta': 300.0, 'n': 0.0, 'e': 0.0},  # curve PI, not IP
+    ]
+    out = ck.normalize_ip_names(drawing)
+    assert [d['name'] for d in out] == ['PC', 'IP', 'PI1']
+
+
+def test_normalize_ip_names_does_not_mutate_input() -> None:
+    drawing = [{'name': 'IP1', 'sta': 100.0, 'n': 0.0, 'e': 0.0}]
+    ck.normalize_ip_names(drawing)
+    assert drawing[0]['name'] == 'IP1'
+
+
+def test_add_pcc_control_points_inserts_at_coincident_pair() -> None:
+    control = [
+        ControlPoint(name='PT', sta=100.000, n=10.0, e=20.0),
+        ControlPoint(name='PC', sta=100.004, n=10.0, e=20.0),
+    ]
+    out = ck.add_pcc_control_points(control)
+    assert len(out) == 3
+    pcc = out[-1]
+    assert pcc.name == 'PCC'
+    assert pcc.sta == pytest.approx(100.002)
+    assert pcc.n == 10.0 and pcc.e == 20.0
+
+
+def test_add_pcc_control_points_ignores_distant_pt_pc() -> None:
+    # A genuine PT...PC with a real tangent between them (not a compound
+    # junction) must not spawn a synthetic PCC.
+    control = [
+        ControlPoint(name='PT', sta=100.0, n=0.0, e=0.0),
+        ControlPoint(name='PC', sta=250.0, n=0.0, e=0.0),
+    ]
+    out = ck.add_pcc_control_points(control)
+    assert len(out) == 2
+
+
+def test_add_pcc_control_points_does_not_mutate_input() -> None:
+    control = [
+        ControlPoint(name='PT', sta=100.000, n=0.0, e=0.0),
+        ControlPoint(name='PC', sta=100.001, n=0.0, e=0.0),
+    ]
+    ck.add_pcc_control_points(control)
+    assert len(control) == 2
```

## หมายเหตุเรื่อง test_data/

`test_data/AL1_test_alignment_PI.csv` และ `test_data/AL1_test_alignment_drawing.csv`
**ถูก CK1024 แก้ไขและวางในโปรเจกต์จริงแล้วโดยตรง** (ไม่ใช่ส่วนหนึ่งของ diff นี้) —
เพิ่มเลขกำกับ `PI1`-`PI11` ที่ระบุ RADIUS ต่างกัน + แก้ `IP`→`IP1`/`IP2` เพื่อความชัดเจน
Claude Code ไม่ต้องแตะไฟล์ 2 ไฟล์นี้เลยในแผนนี้

## ผลตรวจสอบก่อนส่งแผน

- `pytest -q` เต็มชุด: **528 passed** (517 หลัง #3 + 11 ใหม่: 6 core-fix tests
  ในสองไฟล์ builders + 6 adapter tests ใน test_check.py - ลบเทสเดิม 4 ตัวที่
  assert พฤติกรรมบั๊กเดิมไว้ตรงๆ ออกไป, เพิ่มสุทธิ 11)
- เทสใหม่ทั้งหมดผ่าน red-green cycle (fail ก่อนแก้ / pass หลังแก้)
- รันจริงกับ `AL1_test_alignment_drawing.csv` (ฉบับที่ CK1024 แก้ไขแล้ว) end-to-end
  ผ่าน `parse_pi_table` → `build_alignment_from_pi` → adapters → `check_against_drawing`
  ได้ผลตรงตามคาดทุกจุด

## เอกสารที่ต้องเขียน (สเต็ปถัดไป หลัง code+tests approve)

- `docs/extensions.md` — entry ใหม่ "Oracle Correction — check_against_drawing
  No-Match Reporting + Station-Distance Ceiling" (เน้นว่าเงื่อนไข (1) เป็น N/A
  เพราะไม่มี oracle port ใดๆ เลย ต่างจาก #1-#3) + entry แยกสำหรับ
  `normalize_ip_names`/`add_pcc_control_points` (ไม่ใช่ Oracle correction —
  เป็น adapter ธรรมดา ระบุเหตุผล/evidence จากข้อมูลจริงตามที่วิเคราะห์ไว้ข้างบน)
- `CLAUDE.md` — Known limits bullet ใหม่ (2 รายการ หรือรวมเป็นรายการเดียวก็ได้)
  + Status header อัปเดตเลข pytest (517→528)
- `session_logs/latest.md` — entry สรุปงานทั้งหมด (core fix + adapter)

## ขั้นตอนแนะนำสำหรับ Claude Code (ทีละสเต็ป ตามกฎ ไม่ batch)

1. apply diff #1 (`alignment_builder.py`) → โชว์ diff จริง → รอ approve
2. apply diff #2 (`vertical_builder.py`) → โชว์ diff จริง → รอ approve
3. apply diff #4+#5 (เทสทั้งสองไฟล์ builders) → รัน
   `pytest tests/builders/ -v -k check_against_drawing` โชว์ raw output → รอ approve
4. apply diff #3 (`check.py` ฟังก์ชันใหม่) → โชว์ diff จริง → รอ approve
5. apply diff #6 (`test_check.py`) → รัน `pytest tests/test_check.py -v` โชว์ raw output → รอ approve
6. รัน `pytest -q` เต็มชุด โชว์ raw output (คาดหวัง 528 passed) → รอ approve
7. เขียน `docs/extensions.md` (2 entries) → โชว์เนื้อหาจริงก่อน save → รอ approve
8. อัปเดต `CLAUDE.md` (Known limits + Status) → โชว์ diff จริง → รอ approve
9. `session_logs/latest.md` append (heredoc) → รอ approve
10. commit message ผ่าน `.git/smt_commit_msg.txt` + `cat -A` เช็ค → commit → โชว์ `git log -3 --oneline`
11. push → ยืนยัน raw `git log` ทั้ง local/origin ตรงกัน
