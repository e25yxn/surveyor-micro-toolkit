# แผนแก้: เพิ่ม chord/delta/tangent/external/midOrd/crvType + `<PI>` ให้ Curve และ Spiral ใน LandXML export

> อ้างอิงรายงานสืบสวนที่อนุมัติสูตรแล้ว: `session_logs/investigate_landxml_curve_pi_attrs.md` (commit `cd9d138`)
> สำเนาแผนนี้ อนุมัติแล้วโดยผู้ใช้ผ่าน plan mode เมื่อ 2026-07-06 (ต้นฉบับ:
> `C:\Users\CK1024\.claude\plans\session-logs-plan-landxml-curve-pi-attr-starry-glacier.md`)

## Context

`export_alignment_landxml` (src/smt/landxml.py) export `<Curve>`/`<Spiral>` ตอนนี้ยังไม่มี
attribute `delta`, `chord`, `tangent`, `external`, `midOrd`, `crvType` และไม่มี `<PI>` sub-tag เลย —
ผู้ใช้งานปลายทาง (Civil 3D, หรือ CAD อื่น) ที่ import LandXML นี้จะไม่เห็นค่าพวกนี้ ทั้งที่เป็น
attribute มาตรฐานของ LandXML 1.2 schema ที่ CAD ส่วนใหญ่คาดหวัง รายงานสืบสวนก่อนหน้า
(`investigate_landxml_curve_pi_attrs.md`, commit cd9d138) ตรวจสอบแล้วว่าตัวแปรที่จำเป็น
(`_theta_rad`, `tan_long` จาก `_spiral_geometry`) มีอยู่แล้วในสโคป ไม่ต้องคำนวณใหม่จากศูนย์ และ
ทดสอบสูตรจริง 2 เส้นทาง (hand-built vertices + CSV→CLI เต็ม pipeline) เทียบกับ Civil 3D ground
truth จริง ได้ผลต่าง 0.008–0.30 มม. ทุกค่า (ไม่ตรงเป๊ะ เพราะ Civil 3D likely คำนวณ alignment
geometry ใหม่เองหลัง import ไม่ preserve ค่าดิบ) แผนนี้เอาผลสรุปนั้นมาทำเป็นโค้ดจริง +
regression test จริงเทียบ ground truth เดียวกัน

**ข้อจำกัดสำคัญที่พบก่อน finalize แผนนี้ (ตรวจสอบแล้ว ไม่ใช่สมมติฐาน):** ตัวเลข Civil 3D ground
truth ในรายงานสืบสวน (tangent/chord/external/midOrd/PI point ของ Curve, PI point ของ SPIN) **ไม่มี
ไฟล์ Civil 3D export จริงในโปรเจกต์รองรับ** — grep ค่าตัวเลขทั้งหมด (เช่น `30.470311074669`,
`1543269.952250064351`) เจอเฉพาะในไฟล์รายงาน `session_logs/investigate_landxml_curve_pi_attrs.md`
เอง ไม่เจอในไฟล์ XML ใดในโปรเจกต์ (`test_data/SettingOutTest555.xml` และ
`test_data/SMT_TEST_CLOTHIOD.csv` ที่เพิ่งถูก copy เข้ามาใหม่เป็นข้อมูลคนละชุด — CSV มี PI table
ตรงกับที่ใช้ในรายงานก็จริง แต่ XML คู่กันเป็น output ของ SMT เอง (ไม่มี attribute ใหม่/`<PI>` เลย
โครงสร้างตรงกับ `export_alignment_landxml` เวอร์ชันปัจจุบันเป๊ะ) ไม่ใช่ Civil 3D export จริง)
ดังนั้นตัวเลข ground truth ที่มีอยู่จึงยืนยันได้แค่ **Curve กับ SPIN** (element index 2 กับ 1 ตาม
รายงาน) เท่านั้น — **SPOUT ไม่มี ground truth อิสระให้เทียบ** ต้องยืนยัน SPOUT ด้วยหลักการ
mirror-symmetry แทน (SPIN/SPOUT ที่มี R และ length เท่ากันต้องได้ `tanLong` ค่าเดียวกัน — ยืนยัน
แล้วโดย `test_spout_geometry_matches_spin` ที่มีอยู่ในไฟล์ test เดิม) บวกกับ self-consistency
check ว่า PI point ที่คำนวณได้อยู่ห่างจาก Start ของ SPOUT เท่ากับ `tanLong` จริง (พิสูจน์ว่าสูตร
เดียวกันถูกใช้ถูกต้อง ไม่ใช่พิสูจน์ว่าตรงกับ Civil 3D) — ดูรายละเอียด test ในหัวข้อสองด้านล่าง
ห้ามเขียน commit message/docstring/comment ใดๆ ที่ทำให้ดูเหมือนว่า SPOUT ถูกยืนยันเทียบ Civil 3D
โดยตรงเหมือน Curve/SPIN

## หนึ่ง — Diff เต็มของ `src/smt/landxml.py`

### 1.1 Import เพิ่ม (บรรทัด ~24)

```diff
 from . import fpmath
+from . import wcb
 from .alignment import (
```

เหตุผล: `wcb.calculate_forward(n1, e1, azimuth, distance) -> Point` มีอยู่แล้ว
(`src/smt/wcb.py:61`, `n=n1+distance*cos(az), e=e1+distance*sin(az)`) — ตรงกับสูตร
"PI = Start + tangent·(cos az, sin az)" ที่รายงานยืนยันแล้วเป๊ะ ใช้ซ้ำแทนเขียน trig เอง

### 1.2 Module docstring (บรรทัด 1-17) — เพิ่มย่อหน้าอธิบาย attribute ใหม่

```diff
 dirStart/dirEnd = entry/exit azimuth converted to Civil 3D direction
 convention (decimal degrees, 0=East counterclockwise) via _to_civil_dir,
 on every Curve.  Spiral has no dirStart/dirEnd (Civil 3D doesn't use them
 there); instead it carries theta (absolute total turning angle, dd) plus
 totalX/totalY/tanLong/tanShort (meters), computed canonically from a
 synthetic Element at the origin curving from k_in=0 to k_out=1/R — these
 values do not depend on the spiral's real position, direction, or role
 (SPIN/SPOUT) in the alignment.
+
+Curve also carries delta (dd, unsigned total turning angle of that Curve
+element only — not the full PI's deflection when spirals flank it),
+chord/tangent/external/midOrd (meters, standard circular-curve formulas from
+R and delta), and crvType="arc" (constant).  Both Curve and Spiral carry a
+<PI> sub-tag (Start + tangent, resp. tanLong, projected along the element's
+entry azimuth via wcb.calculate_forward) — for Spiral this is the PI local
+to that spiral's own tangent line, not the alignment vertex PI.
+These six new values are a close approximation of Civil 3D's own reported
+values (observed diff 0.008-0.30 mm across two ground-truth curves/spirals),
+not an exact reproduction — see
+session_logs/investigate_landxml_curve_pi_attrs.md for the verification and
+the likely reason (Civil 3D re-derives geometry on import rather than
+preserving raw exported values).
 """
```

### 1.3 `export_alignment_landxml` docstring (บรรทัด ~136-143)

```diff
     Curve: <Center> child tag; dirStart/dirEnd (entry/exit azimuth, Civil 3D
     direction convention, decimal degrees).
+    Curve also carries delta/chord/tangent/external/midOrd (meters/dd,
+    standard circular-curve formulas — see module docstring) and
+    crvType="arc"; both Curve and Spiral carry a <PI> sub-tag.  These values
+    approximate Civil 3D within ~0.5 mm, not exact (see module docstring).
     Spiral: no dirStart/dirEnd; theta (absolute total turning angle, decimal
```

### 1.4 Curve branch (บรรทัด 184-197 ปัจจุบัน)

**ก่อน:**
```python
        elif el.type == 'C':
            k = el.k_in
            R = abs(1.0 / k)
            cn, ce = _curve_center(el.n, el.e, el.azimuth, k)
            exit_az = _exit_azimuth(i, elements)
            tag = ET.SubElement(coord_geom, f'{{{_NS}}}Curve',
                                rot=_rotation(k),
                                radius=f'{R:.6f}',
                                length=f'{length:.6f}',
                                dirStart=f'{_to_civil_dir(el.azimuth):.6f}',
                                dirEnd=f'{_to_civil_dir(exit_az):.6f}')
            _sub(tag, 'Start',  _coord(el.n, el.e))
            _sub(tag, 'Center', _coord(cn, ce))
            _sub(tag, 'End',    _coord(end_n, end_e))
```

**หลัง:**
```python
        elif el.type == 'C':
            k = el.k_in
            R = abs(1.0 / k)
            cn, ce = _curve_center(el.n, el.e, el.azimuth, k)
            exit_az = _exit_azimuth(i, elements)
            delta_rad = _theta_rad(el.azimuth, exit_az)
            half_delta = delta_rad / 2.0
            tangent = R * math.tan(half_delta)
            chord = 2.0 * R * math.sin(half_delta)
            external = R * (1.0 / math.cos(half_delta) - 1.0)
            mid_ord = R * (1.0 - math.cos(half_delta))
            pi_point = wcb.calculate_forward(el.n, el.e, el.azimuth, tangent)
            tag = ET.SubElement(coord_geom, f'{{{_NS}}}Curve',
                                rot=_rotation(k),
                                radius=f'{R:.6f}',
                                length=f'{length:.6f}',
                                dirStart=f'{_to_civil_dir(el.azimuth):.6f}',
                                dirEnd=f'{_to_civil_dir(exit_az):.6f}',
                                delta=f'{fpmath.rad_to_deg(delta_rad):.6f}',
                                chord=f'{chord:.6f}',
                                tangent=f'{tangent:.6f}',
                                external=f'{external:.6f}',
                                midOrd=f'{mid_ord:.6f}',
                                crvType='arc')
            _sub(tag, 'Start',  _coord(el.n, el.e))
            _sub(tag, 'Center', _coord(cn, ce))
            _sub(tag, 'End',    _coord(end_n, end_e))
            _sub(tag, 'PI',     _coord(pi_point.n, pi_point.e))
```

ของเดิมทั้งหมด (`rot`, `radius`, `length`, `dirStart`, `dirEnd`, `Start`/`Center`/`End` sub-tag)
**ไม่เปลี่ยนค่าและไม่เปลี่ยนลำดับการคำนวณ** — เป็นการแทรกบรรทัดคำนวณเพิ่มก่อนสร้าง tag
แล้วต่อท้าย attribute list กับต่อท้าย sub-tag list เท่านั้น

### 1.5 SPIN branch (บรรทัด 199-218 ปัจจุบัน) — เพิ่ม `<PI>` เท่านั้น (ไม่มี attribute ใหม่)

**ก่อน:**
```python
        elif el.type == 'SPIN':
            k_out = el.k_out
            R_out = abs(1.0 / k_out)
            exit_az = _exit_azimuth(i, elements)
            theta_rad = _theta_rad(el.azimuth, exit_az)
            total_x, total_y, tan_long, tan_short = _spiral_geometry(
                R_out, length, el.transition, theta_rad)
            tag = ET.SubElement(coord_geom, f'{{{_NS}}}Spiral',
                                rot=_rotation(k_out),
                                radiusStart='INF',
                                radiusEnd=f'{R_out:.6f}',
                                spiType=_spiral_lx_type(el.transition),
                                length=f'{length:.6f}',
                                theta=f'{fpmath.rad_to_deg(theta_rad):.6f}',
                                totalX=f'{total_x:.6f}',
                                totalY=f'{total_y:.6f}',
                                tanLong=f'{tan_long:.6f}',
                                tanShort=f'{tan_short:.6f}')
            _sub(tag, 'Start', _coord(el.n, el.e))
            _sub(tag, 'End',   _coord(end_n, end_e))
```

**หลัง:**
```python
        elif el.type == 'SPIN':
            k_out = el.k_out
            R_out = abs(1.0 / k_out)
            exit_az = _exit_azimuth(i, elements)
            theta_rad = _theta_rad(el.azimuth, exit_az)
            total_x, total_y, tan_long, tan_short = _spiral_geometry(
                R_out, length, el.transition, theta_rad)
            pi_point = wcb.calculate_forward(el.n, el.e, el.azimuth, tan_long)
            tag = ET.SubElement(coord_geom, f'{{{_NS}}}Spiral',
                                rot=_rotation(k_out),
                                radiusStart='INF',
                                radiusEnd=f'{R_out:.6f}',
                                spiType=_spiral_lx_type(el.transition),
                                length=f'{length:.6f}',
                                theta=f'{fpmath.rad_to_deg(theta_rad):.6f}',
                                totalX=f'{total_x:.6f}',
                                totalY=f'{total_y:.6f}',
                                tanLong=f'{tan_long:.6f}',
                                tanShort=f'{tan_short:.6f}')
            _sub(tag, 'Start', _coord(el.n, el.e))
            _sub(tag, 'End',   _coord(end_n, end_e))
            _sub(tag, 'PI',    _coord(pi_point.n, pi_point.e))
```

### 1.6 SPOUT branch (บรรทัด 220-239 ปัจจุบัน) — เหมือนกัน ใช้ `R_in`/`k_in`

**ก่อน:**
```python
        elif el.type == 'SPOUT':
            k_in = el.k_in
            R_in = abs(1.0 / k_in)
            exit_az = _exit_azimuth(i, elements)
            theta_rad = _theta_rad(el.azimuth, exit_az)
            total_x, total_y, tan_long, tan_short = _spiral_geometry(
                R_in, length, el.transition, theta_rad)
            tag = ET.SubElement(coord_geom, f'{{{_NS}}}Spiral',
                                rot=_rotation(k_in),
                                radiusStart=f'{R_in:.6f}',
                                radiusEnd='INF',
                                spiType=_spiral_lx_type(el.transition),
                                length=f'{length:.6f}',
                                theta=f'{fpmath.rad_to_deg(theta_rad):.6f}',
                                totalX=f'{total_x:.6f}',
                                totalY=f'{total_y:.6f}',
                                tanLong=f'{tan_long:.6f}',
                                tanShort=f'{tan_short:.6f}')
            _sub(tag, 'Start', _coord(el.n, el.e))
            _sub(tag, 'End',   _coord(end_n, end_e))
```

**หลัง:**
```python
        elif el.type == 'SPOUT':
            k_in = el.k_in
            R_in = abs(1.0 / k_in)
            exit_az = _exit_azimuth(i, elements)
            theta_rad = _theta_rad(el.azimuth, exit_az)
            total_x, total_y, tan_long, tan_short = _spiral_geometry(
                R_in, length, el.transition, theta_rad)
            pi_point = wcb.calculate_forward(el.n, el.e, el.azimuth, tan_long)
            tag = ET.SubElement(coord_geom, f'{{{_NS}}}Spiral',
                                rot=_rotation(k_in),
                                radiusStart=f'{R_in:.6f}',
                                radiusEnd='INF',
                                spiType=_spiral_lx_type(el.transition),
                                length=f'{length:.6f}',
                                theta=f'{fpmath.rad_to_deg(theta_rad):.6f}',
                                totalX=f'{total_x:.6f}',
                                totalY=f'{total_y:.6f}',
                                tanLong=f'{tan_long:.6f}',
                                tanShort=f'{tan_short:.6f}')
            _sub(tag, 'Start', _coord(el.n, el.e))
            _sub(tag, 'End',   _coord(end_n, end_e))
            _sub(tag, 'PI',    _coord(pi_point.n, pi_point.e))
```

**หมายเหตุเรื่องตำแหน่ง `<PI>`:** วางเป็น sub-tag ตัวสุดท้าย (ต่อจาก `End`) ทั้ง Curve และ
Spiral — ไม่มีไฟล์ Civil 3D ground truth ที่มี `<PI>` sub-tag อยู่ในโปรเจกต์ตอนนี้ให้เทียบลำดับ
จริง (รายงานสืบสวนก็ระบุไว้ชัดว่ายังไม่ได้ออกแบบเรื่องนี้) จึงเลือกวิธีที่เสี่ยงน้อยที่สุด: ต่อท้าย
โดยไม่แตะลำดับ tag เดิม ถ้าพบไฟล์ Civil 3D จริงที่มี `<PI>` ในอนาคตแล้วลำดับต่างจากนี้ ค่อยแก้
ลำดับใหม่แยกเป็นงานเล็กภายหลัง (ไม่กระทบ attribute values ใดๆ)

## สอง — Test ใหม่ใน `tests/test_landxml.py`

เพิ่ม helper vertex + test class ใหม่ท้ายไฟล์ (ต่อจาก `TestAnglePoint`), ใช้ PI table เดียวกับ
รายงานสืบสวนเป๊ะ (BP/PI1 R=100 Ls=35 CLOTHOID/PI2 R=-105 Ls=40 CLOTHOID/EP):

```python
def _verts_pi_table_ground_truth():
    """PI table verified against a real Civil 3D LandXML export within 0.5 mm
    for Curve tangent/chord/external/midOrd/PI and Spiral(SPIN) PI --
    see session_logs/investigate_landxml_curve_pi_attrs.md."""
    return [
        {'n': 1543078.851, 'e': 682175.2221},
        {'n': 1543275.044, 'e': 682214.0623, 'R': 100.0,  'Ls': 35.0, 'trans': 'CLOTHOID'},
        {'n': 1543368.699, 'e': 682416.2292, 'R': -105.0, 'Ls': 40.0, 'trans': 'CLOTHOID'},
        {'n': 1543573.554, 'e': 682458.492},
    ]


def _verts_curve_left():
    """Left-hand circular curve R=300 (mirrors _verts_curve but ccw)."""
    return [
        {'n':    0.0, 'e':   0.0},
        {'n':    0.0, 'e': 500.0, 'R': 300.0},
        {'n':  500.0, 'e': 500.0},
    ]


class TestCurvePISubTagCivil3D:
    """Ground truth Civil 3D LandXML numbers from
    session_logs/investigate_landxml_curve_pi_attrs.md.  Tolerance is 0.5 mm
    (5e-4 m), NOT the 1e-6 used by the synthetic-input tests elsewhere in this
    file: the report found 0.008-0.30 mm differences from Civil 3D's own
    reported values (likely because Civil 3D re-derives alignment geometry
    on import instead of preserving what we export) -- these new attributes
    are a close approximation, not an exact reproduction.
    """
    _TOL = 5e-4   # 0.5 mm -- see session_logs/investigate_landxml_curve_pi_attrs.md

    def test_curve_tangent_chord_external_midord(self):
        xml = export_alignment_landxml(_build(_verts_pi_table_ground_truth()))
        root = _parse(xml)
        curve = _find_all(root, 'Curve')[0]
        assert math.isclose(float(curve.get('tangent')),  30.470311074669, abs_tol=self._TOL)
        assert math.isclose(float(curve.get('chord')),     58.294529362525, abs_tol=self._TOL)
        assert math.isclose(float(curve.get('external')),   4.539178574294, abs_tol=self._TOL)
        assert math.isclose(float(curve.get('midOrd')),     4.342083643854, abs_tol=self._TOL)

    def test_curve_crv_type_is_arc(self):
        xml = export_alignment_landxml(_build(_verts_pi_table_ground_truth()))
        root = _parse(xml)
        curve = _find_all(root, 'Curve')[0]
        assert curve.get('crvType') == 'arc'

    def test_curve_pi_point(self):
        xml = export_alignment_landxml(_build(_verts_pi_table_ground_truth()))
        root = _parse(xml)
        curve = _find_all(root, 'Curve')[0]
        pi_n, pi_e = _ne(curve, 'PI')
        assert math.isclose(pi_n, 1543269.952250064351, abs_tol=self._TOL)
        assert math.isclose(pi_e,  682220.539152466343, abs_tol=self._TOL)

    def test_spin_pi_point_matches_civil3d(self):
        """SPIN only -- this is the one spiral element the investigation report
        has an independent Civil 3D ground-truth number for.  There is no
        equivalent ground truth for SPOUT in this project (see class
        TestSpoutPISelfConsistency below for why, and how SPOUT is verified
        instead)."""
        xml = export_alignment_landxml(_build(_verts_pi_table_ground_truth()))
        root = _parse(xml)
        spin = next(s for s in _find_all(root, 'Spiral') if s.get('radiusStart') == 'INF')
        pi_n, pi_e = _ne(spin, 'PI')
        assert math.isclose(pi_n, 1543230.641722853528, abs_tol=self._TOL)
        assert math.isclose(pi_e,  682205.272023039055, abs_tol=self._TOL)


class TestSpoutPISelfConsistency:
    """SPOUT PI point has NO independent Civil 3D ground truth in this project
    (checked: grepped the whole repo for the report's ground-truth numbers,
    only the report itself contains them; the only two XML/CSV files that
    looked like candidates -- test_data/SettingOutTest555.xml and
    test_data/SMT_TEST_CLOTHIOD.csv -- are a different PI table and an SMT-own
    export respectively, not a Civil 3D export of *this* PI table's SPOUT).

    So SPOUT is verified two other ways instead, NEITHER of which is
    equivalent to an independent Civil-3D comparison:
    1. mirror-symmetry: test_spout_geometry_matches_spin (existing test,
       TestSpiralIn class) already proves SPIN and SPOUT compute the same
       tanLong/tanShort/totalX/totalY when R and length match.
    2. self-consistency (this test): SPOUT's own PI point must sit at
       distance `tanLong` from SPOUT's own Start, along SPOUT's own entry
       azimuth -- proves the PI formula was applied correctly to the SPOUT
       branch's variables, not that the result matches Civil 3D.
    """

    def test_spout_pi_distance_equals_tan_long(self):
        xml = export_alignment_landxml(_build(_verts_pi_table_ground_truth()))
        root = _parse(xml)
        spout = next(s for s in _find_all(root, 'Spiral') if s.get('radiusEnd') == 'INF')
        tan_long = float(spout.get('tanLong'))
        pi_n, pi_e = _ne(spout, 'PI')
        sn, se = _ne(spout, 'Start')
        assert math.isclose(math.hypot(pi_n - sn, pi_e - se), tan_long, abs_tol=1e-6)


class TestCurvePIGeometricInvariant:
    """Formula-independent regression check (tight 1e-6 tolerance, no Civil 3D
    ground truth needed): for a simple circular curve, PI is equidistant from
    curve Start and curve End, and both distances equal `tangent` -- true for
    both right (_verts_curve) and left (_verts_curve_left) turns.  Guards
    against the R-sign bug class called out in
    session_logs/investigate_landxml_curve_pi_attrs.md section 5 (formula
    must use R=abs(1/k), not el.k_in directly)."""

    def test_pi_equidistant_from_start_and_end(self):
        for verts in (_verts_curve(), _verts_curve_left()):
            xml = export_alignment_landxml(_build(verts))
            root = _parse(xml)
            curve = _find_all(root, 'Curve')[0]
            tangent = float(curve.get('tangent'))
            pi_n, pi_e = _ne(curve, 'PI')
            sn, se = _ne(curve, 'Start')
            en, ee = _ne(curve, 'End')
            assert math.isclose(math.hypot(pi_n - sn, pi_e - se), tangent, abs_tol=1e-6)
            assert math.isclose(math.hypot(pi_n - en, pi_e - ee), tangent, abs_tol=1e-6)
```

**เรื่อง "ยืนยัน attribute เดิมไม่เปลี่ยน" (ข้อ 3 ที่ผู้ใช้ขอ):** ไม่เพิ่ม test ใหม่ซ้ำซ้อน —
ไฟล์นี้มี test เดิมอยู่แล้วที่ assert ตรงบน attribute เดิมทุกตัวที่เกี่ยวข้อง
(`test_radius_attribute`, `test_curve_dir_start`, `test_curve_dir_end`, `test_rotation_cw`,
`test_spin_geometry_attributes`, `test_spout_geometry_matches_spin`,
`test_cosine_total_x_uses_closed_form_not_arc_length` ฯลฯ) — การรัน `pytest -q` เต็มชุดแล้วผ่าน
ทั้งหมด (ข้อห้าด้านล่าง) **คือ** หลักฐานยืนยันว่า attribute เดิมไม่เปลี่ยน เพิ่ม test ซ้ำแค่เพื่อ
บอกอย่างเดียวกันจะขัดหลัก "อย่าเพิ่ม abstraction/ของซ้ำเกินจำเป็น" ใน CLAUDE.md

## สาม — ยืนยัน attribute เดิมไม่เปลี่ยน

Diff ทั้งหมดในข้อหนึ่งเป็นการ **แทรกบรรทัดคำนวณใหม่ก่อนสร้าง tag + ต่อท้าย attribute list +
ต่อท้าย sub-tag list** เท่านั้น ไม่มีบรรทัดใดลบหรือแก้ไขค่าเดิม:
`rot`, `radius`, `length`, `dirStart`, `dirEnd` (Curve), `rot`, `radiusStart`, `radiusEnd`,
`spiType`, `length`, `theta`, `totalX`, `totalY`, `tanLong`, `tanShort` (Spiral),
`Start`/`Center`/`End` sub-tag ทั้งหมด — ค่าและลำดับการคำนวณเดิมเหมือนเดิมทุกตัว

## สี่ — Docstring ระบุว่าเป็นค่าประมาณ

ระบุไว้แล้วในข้อ 1.2/1.3 ด้านบน (module docstring + function docstring) — ระบุขนาดผลต่างจริง
(0.008–0.30 มม.) เหตุผลที่เป็นไปได้ (Civil 3D re-derive geometry เอง ไม่ preserve ค่าดิบ) และ
อ้างอิง `session_logs/investigate_landxml_curve_pi_attrs.md`

## ห้า — Verification (ยังไม่รันตอนนี้ ระบุไว้เป็นขั้นตอนหลัง implement)

1. `pytest -q` เต็มชุด (ต้องผ่านทั้งหมด รวม test เดิม 407+ ตัว บวก test ใหม่ 6 ตัวในแผนนี้ — 4 ตัว
   เทียบ Civil 3D ground truth จริงของ Curve+SPIN ใน `TestCurvePISubTagCivil3D`, 1 ตัว self-
   consistency ของ SPOUT ใน `TestSpoutPISelfConsistency`, 1 ตัว geometric invariant ของ Curve
   ซ้าย/ขวาใน `TestCurvePIGeometricInvariant`)
2. รัน `smt export-landxml` จริงกับ `test_data/SettingOutTest.csv` หรือไฟล์ CSV จริงอื่นที่มีอยู่
   แล้วเปิดดู XML ที่ได้ด้วยตาเพื่อ sanity-check ว่า `<PI>`/attribute ใหม่ออกมาเป็นตัวเลขสมเหตุสมผล
   (ไม่ NaN, ไม่ negative ที่ควรเป็นบวก) — เป็น smoke test ตามข้อตกลง CLAUDE.md ส่วนที่ 8
3. หลังผ่านทั้งหมด: เขียน commit message ลง `.git\smt_commit_msg.txt` แล้ว
   `git commit -F .git\smt_commit_msg.txt` ตามมาตรฐานส่วนที่ 5, บันทึก session_logs/latest.md
   ตามส่วนที่ 1

## ความเสี่ยง

- ต่ำ: ไม่แก้ signature หรือค่าเดิมใดๆ, ไม่มี test เดิมอ้างอิงถึง attribute/tag ที่ยังไม่มี (ยืนยัน
  แล้วในรายงานสืบสวนข้อห้า — grep ทั้งไฟล์ test ไม่เจอการอ้างอิง chord/delta/tangent/external/
  midOrd/PI เลย)
- ความเสี่ยงเดียวที่มี: ตำแหน่ง `<PI>` sub-tag อาจไม่ตรงกับที่ Civil 3D คาดหวังตอน**นำเข้า**กลับ
  (import) แต่แผนนี้ไม่ได้อ้างว่าแก้ import — เป็นแค่ export เพิ่ม attribute ที่ยังไม่มี ถ้าพบปัญหา
  ตอน import จริงในอนาคต ค่อยแก้ลำดับแยกเป็นงานใหม่ (มีไฟล์ ground truth จริงมาเทียบก่อนค่อยแก้)
- ข้อจำกัดที่ทราบแล้วและตั้งใจปล่อยไว้ (ไม่ใช่บั๊ก): SPOUT PI point ไม่มีไฟล์ Civil 3D ground truth
  อิสระในโปรเจกต์ให้เทียบ (ดู Context ด้านบน) ยืนยันได้แค่ mirror-symmetry + self-consistency
  ไม่เท่ากับระดับความมั่นใจของ Curve/SPIN ถ้าในอนาคตมีไฟล์ Civil 3D export จริงที่ครอบคลุม PI table
  เดียวกันนี้ (BP/PI1 R=100 Ls=35/PI2 R=-105 Ls=40/EP) ควรกลับมาเพิ่ม
  `test_spout_pi_point_matches_civil3d` ให้ครบเท่า SPIN
