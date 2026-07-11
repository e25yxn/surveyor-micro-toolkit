# แผน: ปิดงานที่เหลือ Phase 2 (LandXML COSINE totalY/tanShort) — เอกสาร + test เท่านั้น

อ้างอิง: `session_logs/investigate_landxml_phase2_totaly_export.md` (สืบสวนแล้ว ยังไม่ commit)
สรุปว่าตัวเลข totalY/tanShort ถูกต้องอัตโนมัติแล้วจาก Phase 1 — แผนนี้**ไม่แก้สูตรคำนวณใดๆ**
เป็นแค่เพิ่ม test + แก้ docstring/เอกสารให้ตรงกับความจริง

## หนึ่ง — เพิ่ม regression test ใน `tests/test_landxml.py`

เพิ่ม test ใหม่ (parametrize 3 จุด R/L ตรงกับที่ใช้ในรายงานสืบสวน) ยืนยันค่า totalY และ tanShort ของ
COSINE spiral เทียบ ground truth ที่มีอยู่แล้ว — ตำแหน่งใกล้กับ
`test_cosine_total_x_uses_closed_form_not_arc_length` (บรรทัด 309-322 ปัจจุบัน) เพื่อให้อยู่กลุ่ม
เดียวกัน

**Ground truth ที่ใช้ (มาจากรายงานสืบสวน ข้อ 2-3):**
| R | L | totalY ground truth | tanShort ground truth | ที่มา |
|---|---|---|---|---|
| 900 | 100 | 1.651062316115 | — (ไม่มีค่า Civil 3D จริงสำหรับจุดนี้ในรายงานเดิม) | Civil 3D จริง (`investigate_sinehalfwave_formula.md` บรรทัด 21) |
| 250 | 50 | 1.484093072531 | 14.928353346451 | Civil 3D จริง (บรรทัด 25, 43) |
| 500 | 70 | 1.4557579182062208 | 20.856652643241134 | a=1 closed form (`plan_cosine_arclength_core_fix.md` Group 1) |

**Tolerance**: `abs_tol=1e-6` (เมตร) พอเพียง — diff จริงที่วัดได้อยู่ระดับ 1e-11 ถึง 1e-14 เท่านั้น
(ดูตารางในรายงานสืบสวน) 1e-6 ยังเผื่อ margin กว้างกว่าความคลาดเคลื่อนจริงมาก แต่ยังแคบพอที่จะจับ
ถ้ามีใครเผลอแก้ core engine ให้ COSINE ผิดอีกในอนาคต (สูงกว่า noise ระดับ Civil 3D digit ที่มี
~12 หลัก)

**รูปแบบ test ที่เสนอ**:
```python
@pytest.mark.parametrize('r,length,y_exact,tan_short_exact', [
    (900.0, 100.0, 1.651062316115, None),
    (250.0,  50.0, 1.484093072531, 14.928353346451),
    (500.0,  70.0, 1.4557579182062208, 20.856652643241134),
])
def test_cosine_total_y_tan_short_match_ground_truth(r, length, y_exact, tan_short_exact):
    """totalY/tanShort for COSINE now flow correctly from the Phase 1 arc-length-
    inversion fix in alignment.py (calculate_point_on_element at d=length) --
    see session_logs/investigate_landxml_phase2_totaly_export.md sections 2-3.
    """
    verts = [...]  # single SPIN-COSINE PI group, R=r, Ls=length (mirror _verts_spiral_cosine style)
    xml = export_alignment_landxml(_build(verts))
    root = _parse(xml)
    spin = next(s for s in _find_all(root, 'Spiral') if s.get('radiusStart') == 'INF')
    assert math.isclose(float(spin.get('totalY')), y_exact, abs_tol=1e-6)
    if tan_short_exact is not None:
        assert math.isclose(float(spin.get('tanShort')), tan_short_exact, abs_tol=1e-6)
```
(R=900/L=100 ไม่มี tanShort ground truth อิสระในรายงานเดิม — ข้ามการเช็คค่านั้นสำหรับจุดนี้เพียงจุด
เดียว ไม่ใส่ค่าคาดเดา)

โครง `verts` ต้องปรับให้ตรงกับ helper ที่มีอยู่แล้วในไฟล์ (`_verts_spiral_cosine()` ใช้ R=400 Ls=60
คงที่ — ต้องขยายให้รับ R/length เป็นพารามิเตอร์ หรือสร้าง vertex list ตรงในบททดสอบเอง โดยอิงรูปแบบ
เดียวกับ `_verts_spiral_cosine()`)

## สอง — แก้ docstring ที่ล้าสมัย 2 จุด

**2.1 `src/smt/landxml.py::_spiral_geometry` (บรรทัด 94-102)**

ตัดข้อความ "totalY/tanShort still use the d=length approximation -- a separate, smaller,
already-documented known limitation" ออก แทนที่ด้วยคำอธิบายที่ตรงความจริง: totalY/tanShort ไม่มี
override ของตัวเอง มาจาก `calculate_point_on_element` ตรงๆ ซึ่งถูกต้องแล้วตั้งแต่ Phase 1 (อ้างอิง
`session_logs/investigate_landxml_phase2_totaly_export.md`) — และเพิ่มโน้ตว่า totalX override
(บรรทัด 111-112) ตอนนี้ redundant แล้ว (ไม่ผิด แค่ซ้ำซ้อน) พร้อมอ้างอิงรายงานเดียวกัน

**2.2 `src/smt/alignment.py` module docstring, Known limitation (3)**

แก้ข้อความที่ทำนายผิด ("landxml.py's _spiral_geometry still computes totalY/tanShort from the
same d=length evaluation... has not itself been updated... remain a smaller, still-open item...
until a follow-up phase updates the export layer") ให้เป็นข้อเท็จจริงที่ยืนยันแล้ว: totalY/tanShort
ใน `landxml.py` ถูกต้องอัตโนมัติแล้วตั้งแต่ Phase 1 apply (ไม่ต้องรอ follow-up phase) อ้างอิง
`session_logs/investigate_landxml_phase2_totaly_export.md`

## สาม — แก้ CLAUDE.md Known limits

บรรทัดที่พูดถึง COSINE ในหัวข้อ "Known limits" (ที่ยังเขียนว่า "x≈s เป็นค่าประมาณ (คลาดเคลื่อนหลัก
มิลลิเมตรที่ d เท่ากับ L)") ล้าสมัยไปแล้วตั้งแต่ Phase 1 (arc-length inversion แก้ปัญหานี้แล้ว) —
อัปเดตให้ตรงกับสถานะปัจจุบัน: อ้างอิง Phase 1/3 (`plan_cosine_arclength_core_fix.md`,
`investigate_phase3_golden_regen_scope.md`) และ Phase 2 (`investigate_landxml_phase2_totaly_export.md`)
พร้อมระบุ known limitation ที่ยังเหลือจริง (s(1)≠length residual 0.036-0.187mm ที่ไม่ลดลงตาม
quadrature, SPOUT mid-curve ยืนยันด้วย boundary invariant เท่านั้น — ทั้งสองยังเป็นข้อจำกัดจริงตาม
`investigate_cosine_arclength_inversion.md` ไม่ได้ล้าสมัย)

## ขอบเขต — ยืนยันชัดเจนว่าไม่แตะ

- ไม่แก้สูตรคำนวณใดๆ ใน `alignment.py`/`landxml.py` (ตัวเลขถูกต้องอยู่แล้ว)
- ไม่แตะ totalX override ที่ redundant (แค่บันทึกไว้ในเอกสาร ไม่ลบโค้ดในแผนนี้ — การลบเป็น cleanup
  แยกต่างหากที่ต้องพิจารณาความเสี่ยงเพิ่ม)
- ไม่แตะ VBA (Phase 4 เดิม ยังไม่เริ่ม)

## Verification

1. `pytest tests/test_landxml.py -k cosine -v` — test ใหม่ผ่าน
2. `pytest -q` เต็มชุด — ต้องยังคงที่ 490 passed, 0 failed (ไม่ regress)
3. อ่าน diff ของ docstring ทั้ง 2 ไฟล์ + CLAUDE.md ก่อน commit ยืนยันไม่มีการเปลี่ยนตัวเลข/สูตร
   เปลี่ยนแค่ข้อความอธิบาย
