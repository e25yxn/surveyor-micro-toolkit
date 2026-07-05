Investigation: COSINE PI-group turning-angle mismatch in alignment_builder.py
วันที่ 2026-07-05
ประเภทงาน ตรวจสอบ/รายงาน พบระหว่างทำ smoke test `smt export-landxml` ของแผน
session_logs/plan_cosine_sinehalfwave_fix.md ยังไม่มีการแก้โค้ดใดๆ ในรอบนี้

สรุปผล
หลังแก้ COSINE ให้ใช้สูตรปิด Civil 3D Sine Half-Wave (session_logs/plan_cosine_sinehalfwave_fix.md)
พบว่า alignment_builder.py::_build_curve_sub_elements สมมติค่ามุมเลี้ยวของ spiral
(theta_in, theta_out) ด้วยสูตรเชิงเส้น theta = Ls/(2R) เพื่อคำนวณความยาวส่วนโค้งวงกลม
(delta_circular = abs_delta - theta_in - theta_out) สูตรนี้ถูกต้องเป๊ะสำหรับ CLOTHOID
BLOSS SINE เพราะทั้งสามชนิดยังใช้กลไก curvature-vs-arc-length integral ที่มี
F(1) เท่ากับ 1/2 เสมอ (มุมเลี้ยวรวมเท่ากับ k คูณ L หาร 2 พอดี ไม่มี error)
แต่ COSINE แบบใหม่ (closed form) มุมเลี้ยวจริงคือ atan(X หารสองเท่าของ R) ซึ่งไม่เท่ากับ
L หารสองเท่าของ R อีกต่อไป ทำให้เกิด mismatch เล็กน้อยเวลาสร้าง alignment ผ่าน
build_alignment_from_pi (ไม่กระทบ parse_alignment_table ที่อ่านตารางตรงๆ)

ตัวอย่างที่พิสูจน์แล้ว (R=900, Ls=100, ทดสอบผ่าน smt export-landxml)
theta_in สมมติ (เชิงเส้น) = Ls หารสองเท่าของ R = 100/(2*900) = 0.05555555555555555 rad = 3.1830988618379066 องศา
theta จริงของ SPIN-COSINE (คำนวณผ่าน calculate_exit_state ที่ d เท่ากับ L) = 0.0555140053634986 rad = 3.180718211195085 องศา
ผลต่างต่อปลายหนึ่งข้าง = 0.002380650642821517 องศา
ผลต่างรวมสองปลาย (theta_in บวก theta_out) = 0.004761301285643034 องศา
ตรงกับที่สังเกตเห็นจริงในไฟล์ export: SPIN spiral รายงาน theta เท่ากับ 3.180718 องศา
ส่วน SPOUT spiral (R,Ls เท่ากัน ในกลุ่มโค้งเดียวกัน) รายงาน theta เท่ากับ 3.185480 องศา
ต่างกัน 0.0048 องศา ตรงกับตัวเลขที่คำนวณไว้ล่วงหน้าเป๊ะ (0.004761 องศา)

ยืนยันว่าไม่ใช่บั๊กจากการแก้ COSINE รอบนี้
1. alignment.py (calculate_point_on_element, SPIN/SPOUT closed form) ถูกต้องและสมมาตร
   ยืนยันด้วย test_cosine_spin_spout_symmetry_matches_civil3d ที่ tests/test_alignment.py
   ให้ theta ของ SPIN กับ SPOUT เท่ากันเป๊ะถึง 1e-9 เมื่อสร้างแยกอิสระด้วย al.make_element
2. alignment_builder.py::_build_curve_sub_elements ไม่ได้ถูกแก้ไขใดๆ ในรอบนี้เลย
   (ตรวจสอบแล้วด้วย git diff ไม่มีการแตะไฟล์นี้)
3. mismatch เกิดเพราะสูตรเชิงเส้นเดิมใน _build_curve_sub_elements (ที่เคยแม่นเป๊ะกับ
   Simpson-based COSINE เดิม) ไม่แม่นกับ COSINE closed-form ใหม่อีกต่อไป เป็นผลกระทบ
   ต่อเนื่องตามธรรมชาติจากการเปลี่ยนกลไกคำนวณ COSINE ไม่ใช่บั๊กแยกในรอบนี้

ผลกระทบที่สังเกตได้
กลุ่มโค้ง COSINE ที่สร้างผ่าน build_alignment_from_pi (PI table / CLI) จะมีมุมเลี้ยวรวม
จริงคลาดเคลื่อนจากมุมเลี้ยวที่ผู้ใช้ตั้งใจ (abs_delta ที่ PI) เล็กน้อย (ระดับ 0.005 องศา
ในตัวอย่างนี้ ขนาดจะเปลี่ยนตาม Ls/R) เพราะความยาวส่วนโค้งวงกลมถูกคำนวณผิดไปเล็กน้อย
ทำให้ SPIN กับ SPOUT ที่ควรมี theta เท่ากัน (ตามที่ Civil 3D ยืนยันแล้ว) กลับรายงาน
theta ต่างกันในผลลัพธ์ export จริง — ไม่กระทบ parse_alignment_table (อ่านตารางตรงๆ
ไม่ผ่านการคำนวณความยาวส่วนโค้งวงกลมนี้)

ขอบเขต ยังไม่แก้ในรอบนี้ อยู่นอกขอบเขตของ session_logs/plan_cosine_sinehalfwave_fix.md
ซึ่งจำกัดเฉพาะ calculate_point_on_element ใน alignment.py เท่านั้น ต้องวางแผนแยก
ภายหลังสำหรับการแก้ _build_curve_sub_elements

จุดที่ต้องแก้ในอนาคต (ยังไม่ทำตอนนี้)
ไฟล์ src/smt/builders/alignment_builder.py ฟังก์ชัน _build_curve_sub_elements
บรรทัด theta_in = ls_in/(2*R) และ theta_out = ls_out/(2*R) ต้องเปลี่ยนเป็นสูตรที่ตรงกับ
transition shape จริงของแต่ละ PI (สำหรับ COSINE ต้องใช้ atan(X/(2R)) แทน ls/(2R))
ต้องออกแบบให้รองรับทุก transition shape ไม่ใช่แก้เฉพาะ COSINE เพราะฟังก์ชันนี้ใช้ร่วมกัน
ทุกชนิด transition

อ้างอิง
session_logs/plan_cosine_sinehalfwave_fix.md — แผนหลักที่แก้ COSINE core engine
session_logs/investigate_sinehalfwave_formula.md — ที่มาของสูตรปิดและ ground truth
smoke test คำสั่งที่ใช้ค้นพบ: smt export-landxml บนไฟล์ทดสอบ R=900 L=100 (SPIN+C+SPOUT
เดียวกัน ที่มุมเลี้ยว PI เท่ากับ 30 องศา)

อัปเดต 2026-07-05 หลัง regenerate tests/golden/tables.json + reference/tables.json
(session_logs/report_xfail_mismatch_20260705.md): ข้อความบรรทัด 41-42 ข้างต้นที่ว่า
"ไม่กระทบ parse_alignment_table" ผิด เมื่อ regenerate ตารางจากผลลัพธ์ของ
build_alignment_from_pi จริง (ตามที่อนุมัติไว้) mismatch นี้ก็ติดเข้าไปในตัวเลขคงที่ของ
ตารางเองด้วย ยืนยันจาก pytest จริง test_chain_has_no_gaps และ
test_exit_state_matches_next_entry (tests/test_alignment.py) พังที่รอยต่อ SPOUT-COSINE
(element 13 ไป 14) ตรวจสอบด้วยสคริปต์แยกอิสระสองวิธี ได้ตัวเลขตรงกัน
วิธีที่หนึ่ง วัด gap จริงจากการเรียก calculate_exit_state(element13) เทียบ azimuth ที่เก็บไว้
ของ element14 ได้ 34.259909453714954 arcsec
วิธีที่สอง คำนวณ mismatch ต่อปลายจาก theta_assumed (เชิงเส้น Ls/(2R)) ลบ theta_real
(สูตรปิดจริงผ่าน calculate_exit_state ของ SPIN-COSINE เดี่ยว R=500 L=70) แล้วคูณสอง
(สองปลาย) ได้ 34.25988550085129 arcsec
สองวิธีตรงกันถึงหลักที่ 6 (34.2599 arcsec ทั้งคู่) ยืนยันว่าเป็นกลไกเดียวกันจริง ไม่ใช่ error
สะสมอื่น
ตัดสินใจ (อนุมัติแล้ว): ไม่ขยายขอบเขตไปแก้ _build_curve_sub_elements ตอนนี้ mark
test_chain_has_no_gaps และ test_exit_state_matches_next_entry เป็น
xfail(strict=True) พร้อม comment อ้างอิงไฟล์นี้แทน รอแผนแยกสำหรับแก้
_build_curve_sub_elements ให้รองรับทุก transition shape ก่อนจึงจะลบ xfail ทั้งสองนี้ได้

อัปเดต 2026-07-05 (รอบสอง): แก้แล้ว
ทำตาม session_logs/investigate_build_curve_sub_elements_fix.md ที่สืบสวนไว้ก่อนหน้า
แก้ _build_curve_sub_elements ให้เรียกมุมหมุนจริงผ่าน synthetic SPIN element +
calculate_exit_state (ฟังก์ชันใหม่ _spiral_turning_angle) แทนสูตรเชิงเส้น Ls/(2R) เดิม
ยืนยันด้วย pytest จริง: รอยต่อ SPOUT-COSINE (element 13 ไป 14) ที่เคยคลาดเคลื่อน
34.26 arcsec ปิดสนิทเป็น 0 arcsec พอดี (element13 exit az และ element14 entry az
เท่ากันถึง bit-level: 154.9999666429316 องศาทั้งคู่) test_chain_has_no_gaps และ
test_exit_state_matches_next_entry ผ่านจริงแล้ว ลบ xfail(strict=True) ออกทั้งสองตัว
tests/golden/tables.json + reference/tables.json regenerate รอบสอง (20 element rows +
20 control rows เปลี่ยน เหมือนกันทุกตัวอักษรทั้งสองไฟล์ ยืนยันด้วย diff) เพื่อให้ตรงกับ
builder ที่แก้แล้ว
บันทึกเป็น docs/extensions.md EXT-003 (ครอบคลุมทั้งการแก้ alignment.py และ
alignment_builder.py ในหมวดเดียวกัน) และ CLAUDE.md Known limits อัปเดตแล้ว
