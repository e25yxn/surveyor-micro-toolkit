Investigation: _build_curve_sub_elements linear-theta assumption (before planning a fix)
วันที่ 2026-07-05
ประเภทงาน ตรวจสอบ/รายงาน ยังไม่มีการแก้โค้ดใดๆ ในรอบนี้ ยังไม่เขียนแผน

สรุปผล
สืบสวนก่อนวางแผนแก้ known limitation ที่บันทึกไว้ใน
session_logs/investigate_cosine_builder_mismatch_20260705.md และ CLAUDE.md Known limits
(alignment_builder.py::_build_curve_sub_elements สมมติมุมเลี้ยว spiral เชิงเส้น
theta เท่ากับ Ls หารสองเท่าของ R ซึ่งไม่ตรงกับ COSINE closed-form ใหม่)

_build_curve_sub_elements เต็มฟังก์ชัน พร้อมบริบท (src/smt/builders/alignment_builder.py
บรรทัด 59-112 ถูกเรียกจาก build_alignment_from_pi บรรทัด 341 เท่านั้น และตัวมันเองเรียกแค่
fpmath.deg_to_rad)

def _build_curve_sub_elements(
    vert: dict[str, Any], abs_delta: float,
) -> tuple[list[dict[str, Any]], str | None]:
    subs: list[dict[str, Any]] = []
    issue: str | None = None

    compound = vert.get('compound')
    if compound:
        used = 0.0
        for i, arc in enumerate(compound):
            r_circular = abs(float(arc['R']))
            if i < len(compound) - 1:
                delta = fpmath.deg_to_rad(float(arc['delta']))
                used += delta
            else:
                delta = abs_delta - used
            if delta < 0:
                issue = 'compound: ผลรวม delta เกินมุมเลี้ยว'
            subs.append({'kind': 'C', 'R': r_circular, 'len': r_circular * delta})
        return subs, issue

    # EXTENSION: beyond oracle — treat missing R or R=0 as an angle point.
    if not vert.get('R'):
        return [], None

    R = abs(float(vert['R']))
    ls_in  = float(vert['LsIn']  if vert.get('LsIn')  is not None else (vert.get('Ls') or 0.0))
    ls_out = float(vert['LsOut'] if vert.get('LsOut') is not None else (vert.get('Ls') or 0.0))

    if ls_in > 0 or ls_out > 0:
        theta_in  = ls_in  / (2.0 * R) if ls_in  > 0 else 0.0
        theta_out = ls_out / (2.0 * R) if ls_out > 0 else 0.0
        delta_circular = abs_delta - theta_in - theta_out
        if delta_circular < 0:
            issue = 'spiral ยาวเกินมุมเลี้ยว (Δ < θsIn+θsOut)'
        trans     = vert.get('trans')
        trans_in  = vert.get('transIn') or trans
        trans_out = vert.get('transOut') or trans
        if ls_in > 0:
            subs.append({'kind': 'SPIN',  'R': R, 'len': ls_in,  'trans': trans_in})
        subs.append({'kind': 'C', 'R': R, 'len': R * delta_circular})
        if ls_out > 0:
            subs.append({'kind': 'SPOUT', 'R': R, 'len': ls_out, 'trans': trans_out})
        return subs, issue

    subs.append({'kind': 'C', 'R': R, 'len': R * abs_delta})
    return subs, issue

ผู้เรียก (build_alignment_from_pi บรรทัด 341):
subs, issue = _build_curve_sub_elements(vertices[v], abs_delta)
subs ถูกส่งต่อไป _calculate_end_displacement (บรรทัด 361 แก้สมการ 2x2 หาความยาว tangent)
และ loop สร้าง sub-element จริง (บรรทัด 383-394) ซึ่ง loop นี้เรียก calculate_exit_state
ต่อ sub-element อยู่แล้ว — เป็น helper ตัวเดียวกับที่รายงานนี้เสนอให้ theta_in/theta_out
เรียกใช้ด้วย

ข้อหนึ่ง จุดที่สมมติ theta เท่ากับ Ls หารสองเท่าของ R ทั้งหมดในไฟล์นี้
มีจุดเดียวเท่านั้น ใช้ 2 ครั้ง (grep ทั้งไฟล์ด้วย
theta_in|theta_out|ls_in|ls_out|delta_circular|2\.0 \* R ยืนยันไม่มีจุดอื่น)
บรรทัด 96 theta_in = ls_in / (2.0 * R) if ls_in > 0 else 0.0
บรรทัด 97 theta_out = ls_out / (2.0 * R) if ls_out > 0 else 0.0
ทั้งสองป้อนเข้าบรรทัด 98 delta_circular = abs_delta - theta_in - theta_out ซึ่งกำหนด
ความยาวส่วนโค้งวงกลม (บรรทัด 106 R * delta_circular) และเช็ค overflow (บรรทัด 99)
ไม่มีฟังก์ชันอื่นในไฟล์นี้ หรือไฟล์อื่นใน src/smt/ ที่ใช้สูตรนี้ (compound branch ข้างบน
บรรทัด 71-84 ใช้แค่ delta ที่ผู้ใช้กำหนดเป็นองศา ไม่มีการสมมติมุมหมุน spiral เลย)
สมมติฐานเดียวกันนี้อยู่ใน oracle ด้วย reference/AlignmentBuilder.gs บรรทัด 53-54
(thIn = LsIn > 0 ? LsIn/(2*R) : 0, thOut เช่นกัน) สูตรเหมือนกันเป๊ะ ดังนั้นการแก้จุดนี้
เป็นการเบี่ยงออกจาก oracle เพิ่มเติมโดยตั้งใจสำหรับ COSINE เท่านั้น อยู่ในหมวดเดียวกับที่
แก้ alignment.py ไปแล้ว (Extension policy ตาม CLAUDE.md)

ข้อสอง ความเป็นไปได้ของการคำนวณมุมหมุนจริงผ่าน synthetic SPIN element
เป็นไปได้จริง ไม่มีปัญหาไก่กับไข่ R, ls_in/ls_out, trans_in/trans_out ทั้งหมดรู้ค่าแล้ว
(parse จาก vert) ตั้งแต่จุดที่ theta_in/theta_out ถูกคำนวณตอนนี้ (บรรทัด 91-93, 101-103)
ไม่มีตัวไหนขึ้นกับมุมหมุนเองเลย สูตรที่เสนอ
def _spiral_turning_angle(R, Ls, trans):
    el = make_element('SPIN', 0.0, Ls, 0.0, 0.0, 0.0, R, None, trans)
    return calculate_exit_state(el).azimuth - el.azimuth
สร้าง Element ชั่วคราวที่จุดกำเนิด entry azimuth ศูนย์ (k_in เท่ากับศูนย์ k_out เท่ากับ
1/R ผ่าน SPIN branch ที่มีอยู่แล้วใน make_element) แล้วอ่านมุมหมุนสะสมจริงจาก
calculate_exit_state ตรงๆ ไม่ใช่ pattern ใหม่ เป็นเทคนิคเดียวกับที่ใช้อยู่แล้ว 2 จุดในโค้ด
src/smt/landxml.py::_spiral_geometry (synthetic SPIN แบบเดียวกัน คำนวณ
totalX/totalY/tanLong/tanShort) และ _calculate_end_displacement ในไฟล์เดียวกันนี้เอง
(บรรทัด 137-157 สร้าง sub-element จากจุดกำเนิดแล้วเรียก calculate_exit_state อยู่แล้ว)
theta_in/theta_out แค่เรียก calculate_exit_state เร็วกว่าที่ _calculate_end_displacement
เรียกอยู่แล้วประมาณ 74 บรรทัด

ข้อสาม พิสูจน์ว่า CLOTHOID BLOSS SINE ไม่กระทบ ด้วยการคำนวณจริง ไม่ใช่แค่อ้างเหตุผล
รันเทียบสูตรเชิงเส้นกับมุมหมุนจริง 6 ชุด R/Ls/trans ครอบคลุมทั้งสามชนิดที่ถูกต้องอยู่แล้ว
CLOTHOID  R= 400 Ls= 60.0  linear=0.075000000000000  real=0.075000000000000  diff=-1.804e-16
BLOSS     R= 400 Ls= 60.0  linear=0.075000000000000  real=0.075000000000000  diff=-1.804e-16
SINE      R= 500 Ls= 70.0  linear=0.070000000000000  real=0.070000000000000  diff=-2.776e-16
CLOTHOID  R= 900 Ls=100.0  linear=0.055555555555556  real=0.055555555555555  diff=1.943e-16
BLOSS     R= 250 Ls= 50.0  linear=0.100000000000000  real=0.100000000000000  diff=3.608e-16
SINE      R= 300 Ls= 80.0  linear=0.133333333333333  real=0.133333333333334  diff=-4.163e-16
diff อยู่ระดับ 1e-16 ทั้งหมด คือ floating point noise ล้วนๆ ไม่ใช่ความต่างของสูตร
ยืนยันตรงกับที่คาดไว้เชิงทฤษฎี ทั้งสามชนิดสอดคล้องกับ F(1) เท่ากับ 1/2 ใน
_shape_integral เสมอ มุมหมุนรวมจริงจึงเท่ากับ k คูณ L หารสอง เท่ากับ Ls หารสองเท่า R
เป๊ะ เหมือนสมมติฐานเชิงเส้นทุกประการ สรุป การเปลี่ยนไปใช้มุมหมุนจริงไม่ทำให้ผลลัพธ์เดิม
ของ CLOTHOID BLOSS SINE เปลี่ยนแม้แต่ค่าเดียว ไม่ว่า R หรือ Ls จะเป็นเท่าไหร่

ข้อสี่ ทุก test ที่ทดสอบฟังก์ชันนี้ทั้งทางตรงและทางอ้อม
_build_curve_sub_elements เป็นฟังก์ชัน private ไม่มี test ตรงเรียกชื่อมันเลยสักตัว
(grep ทั้ง tests/ แล้วไม่พบการ import หรือเรียกชื่อฟังก์ชันนี้ตรงๆ) ถูกทดสอบทางอ้อมผ่าน
build_alignment_from_pi เท่านั้น ซึ่งถูกใช้ใน 3 ไฟล์ test รวม 110 tests ที่ collect ได้
(pytest --collect-only)
- tests/builders/test_alignment_builder.py เรียก build_alignment_from_pi 33 จุด
  ครอบคลุม test ส่วนใหญ่ในไฟล์นี้ เฉพาะ test ที่ใช้ PI vertex ที่มี Ls/LsIn/LsOut มากกว่า
  ศูนย์เท่านั้นที่ไปถึงบรรทัด 96-98 จริง (test ประเภท type/name/simple-circle/angle-point/
  compound ไม่ไปถึงเลย) ในกลุ่มที่ไปถึง มีแค่ test ที่มาจาก golden-fixture reconstruction
  (TestGoldenElementGeometry, TestGoldenControlPoints, TestChainContinuity ที่ประกอบด้วย
  9 กลุ่มโค้งรวม COSINE) เท่านั้นที่จะเห็นความเปลี่ยนแปลงเชิงตัวเลขได้จริง — ตรงกับที่มาของ
  2 test ที่ xfail อยู่ตอนนี้พอดี (test_chain_has_no_gaps, test_exit_state_matches_next_entry
  ใน tests/test_alignment.py ไม่ใช่ไฟล์นี้ ส่วนตัวที่ใกล้เคียงในไฟล์นี้เองผ่านอยู่แล้ว
  เพราะ fixture ที่ regenerate มาใช้ builder ตัวเดียวกันที่ยังไม่แม่นอยู่แล้ว)
  test_spiral_overflow_reported_as_issue (R=100 Ls=1000 default CLOTHOID trans) และ
  test_ls_zero_treated_as_simple_circle ก็แตะ spiral path เหมือนกัน แต่ assert แค่จำนวน/
  ชนิด issue ไม่ใช่ตำแหน่งตัวเลข ไม่กระทบไม่ว่าจะแก้หรือไม่แก้ ตามข้อสาม
- tests/test_landxml.py มี fixture helper 1 ตัว (_build ครอบ build_alignment_from_pi)
  ใช้ทั่วทั้ง spiral-export test spiral vertex เดียวที่มี (_verts_spiral) ใช้ trans
  default (CLOTHOID) ไม่กระทบตามข้อสาม การอ้างอิง COSINE จุดเดียวในไฟล์นี้คือ test
  string-mapping ที่ไม่เกี่ยวข้อง (_spiral_lx_type('COSINE') เท่ากับ 'sineHalfWave')
- tests/test_optimizer.py เรียก build_alignment_from_pi 6 จุด แต่ทุกตาราง PI ที่สร้างมี
  แค่คอลัมน์ POINT,N,E,STA,R (ไม่มีคอลัมน์ Ls/LsIn/LsOut/Trans เลย) ไม่มีทางไปถึง spiral
  branch (บรรทัด 95-109) เลย ไม่กระทบไม่ว่ากรณีใด

สรุปท้าย การแก้จุดนี้กระทบเฉพาะ 2 test ที่ xfail อยู่ตอนนี้ (จะกลับมา pass จริง) และไม่
กระทบ test อื่นเลยสักตัวจาก 110 test ที่ collect ได้ในสามไฟล์นี้

อ้างอิง
session_logs/investigate_cosine_builder_mismatch_20260705.md — จุดที่ค้นพบปัญหานี้ครั้งแรก
session_logs/plan_cosine_sinehalfwave_fix.md — แผนที่แก้ alignment.py core engine
CLAUDE.md ส่วน Known limits — บันทึกปัญหานี้ไว้แล้ว
