Investigation: Sine Half-Wavelength Diminishing Tangent spiral formula
วันที่ 2026-07-04
ประเภทงาน ตรวจสอบ/รายงาน อ่านและคำนวณมือเทียบ ground truth เท่านั้น ยังไม่มีการแก้โค้ด
สรุปผล
BLOSS และ SINE ในโค้ดปัจจุบัน (_shape_integral ใน alignment.py) ตรงกับสูตรทางการของ Autodesk 100 เปอร์เซ็นต์ ไม่ต้องแก้อะไร ยืนยันด้วยการแปลงสูตรทางคณิตศาสตร์ตรงกันทุกพจน์
COSINE (Civil 3D เรียก Sine Half-Wavelength Diminishing Tangent Curve) ไม่ตรงกับ Civil 3D เพราะใช้คนละกลไกทางคณิตศาสตร์เลย ไม่ใช่แค่ค่าคงที่ผิด CLOTHOID BLOSS SINE ทั้งหมดนิยาม curvature เป็นฟังก์ชันของ arc length ตรงตามที่ SMT ใช้ Simpson integration อยู่ แต่ Sine Half-Wavelength นิยามด้วยระยะที่ฉายลงเส้นสัมผัสตรง (tangent projected distance) ไม่ใช่ arc length ตามเอกสารทางการของ Autodesk

สูตรที่ถูกต้อง (อ้างอิงจาก Autodesk Civil 3D 2026 Help หัวข้อ About Transition Definitions)
หา X จาก L และ R ด้วยสูตรปิด ไม่ต้องแก้สมการวนซ้ำ
X = L - 0.0226689447 times L ยกกำลังสาม หารด้วย R ยกกำลังสอง
หา totalY ปลายโค้ง
Y = 0.14867881635766 times X ยกกำลังสอง หารด้วย R
หามุมเบี่ยงปลายโค้ง (อนุพันธ์ของ y เทียบ x ที่ x เท่ากับ X ค่า sin ของ pi หายไปพอดี เหลือแค่พจน์เชิงเส้น)
theta เท่ากับ arctan ของ X หารด้วยสองเท่าของ R
รูปแบบเต็มของเส้นโค้งเป็นฟังก์ชัน y ของ x โดย a เท่ากับ x หารด้วย X (x วัดตามแนวเส้นสัมผัสเริ่มต้นที่ต่อยาวออกไป ไม่ใช่ arc length)
y เท่ากับ X ยกกำลังสอง หารด้วย R คูณด้วยผลรวมของ a ยกกำลังสองหารสี่ ลบด้วยหนึ่งหารด้วยสองเท่าของ pi ยกกำลังสอง คูณด้วยหนึ่งลบ cos ของ a คูณ pi

ยืนยันด้วยการคำนวณมือ เทียบ ground truth 2 ชุดอิสระ ตามกฎ CLAUDE.md ที่ต้องมีอย่างน้อย 2 จุดต่อ shape
จุดที่หนึ่ง R เท่ากับ 900 L เท่ากับ 100 จากไฟล์ smt-test1.xml
คำนวณได้ X เท่ากับ 99.972014 theta เท่ากับ 3.178945 องศา totalY เท่ากับ 1.651063
ค่าจริงจาก Civil 3D theta เท่ากับ 3.178942026888 องศา totalY เท่ากับ 1.651062316115
ตรงกันในหลักที่ห้าถึงหก ความต่างเป็นแค่ error จากการคำนวณมือ
จุดที่สอง R เท่ากับ 250 L เท่ากับ 50 จากไฟล์ SMT_TEST_ALINGMENT2.xml
คำนวณได้ X เท่ากับ 49.954662 theta เท่ากับ 5.70535 องศา totalY เท่ากับ 1.484093
ค่าจริงจาก Civil 3D totalX เท่ากับ 49.954662110533 theta เท่ากับ 5.705449190899 องศา totalY เท่ากับ 1.484093072531
ตรงกันในหลักที่ห้าถึงเก้า
สรุป สูตรนี้ถูกต้อง ผ่านการยืนยันครบตามเกณฑ์สองจุดข้อมูลแล้ว
ช่องว่างที่ยังไม่ได้พิสูจน์ ต้องระบุตรงๆ
สิ่งที่พิสูจน์แล้วคือค่าที่ปลายโค้งเท่านั้น (totalX totalY theta สำหรับ LandXML export)
จุดกลางโค้ง ที่ alignment.py ต้องใช้ตอนคำนวณ station to coordinate กลางสไปรัลชนิดนี้ ยังไม่มีข้อมูล Civil 3D ยืนยัน เพราะไฟล์ที่มีให้ค่าปลายโค้งต่อ segment เท่านั้น ไม่มีจุดกลาง
ต้องตัดสินใจว่าจะใช้ x ประมาณเท่ากับ s เป็นค่าประมาณสำหรับจุดกลางไปก่อน หรือรอข้อมูลจุดกลางจริงมายืนยันก่อนขยายไปถึง alignment.py core engine
ข้อเสนอจุดที่ควรแก้ ยังไม่ลงมือ รอ Plan-Review-Approve
แก้ src/smt/landxml.py เพิ่ม branch เฉพาะสำหรับ COSINE ใน _spiral_geometry ใช้สูตรปิดข้างบนแทนการเรียก canonical Simpson integration แบบเดียวกับ shape อื่น
ยังไม่เปลี่ยนชื่อ COSINE ในโค้ดตามที่ระบุไว้ใน CLAUDE.md Roadmap จะเปลี่ยนชื่อพร้อมกันหลังแก้สูตรเสร็จเท่านั้น
ยังไม่ตัดสินใจว่า alignment.py core engine จำเป็นต้องแก้ด้วยหรือไม่ รอพิจารณาแยกต่างหาก

อ้างอิง
Autodesk Civil 3D 2026 Help About Transition Definitions
https://help.autodesk.com/cloudhelp/2026/ENG/Civil3D-UserGuide/files/GUID-DD7C0EA1-8465-45BA-9A39-FC05106FD822.htm
smt-test1.xml และ SMT_TEST_ALINGMENT2.xml เป็นไฟล์ Civil 3D ground truth export จริง

ยืนยันเพิ่มเติม SPIN กับ SPOUT ที่ R,L เท่ากัน ให้ theta totalX totalY tanLong tanShort เท่ากันทุกตัว Civil 3D R เท่ากับ 250 L เท่ากับ 50 จาก SMT_TEST_ALINGMENT2.xml ก่อนไฟล์หายจากเครื่อง
SPIN radiusStart เท่ากับ INF radiusEnd เท่ากับ 250 theta เท่ากับ 5.705449190899 องศา totalY เท่ากับ 1.484093072531 totalX เท่ากับ 49.954662110533 tanLong เท่ากับ 35.100262042251 tanShort เท่ากับ 14.928353346451
SPOUT radiusStart เท่ากับ 250 radiusEnd เท่ากับ INF theta totalY totalX tanLong tanShort เท่ากับ SPIN ทุกตัวเลขเป๊ะ
สรุป ยืนยัน mirror-symmetry ระหว่าง SPIN SPOUT ด้วยข้อมูล Civil 3D จริง ไม่ใช่ข้อสันนิษฐาน ใช้แนวทางเดียวกับ CLOTHOID BLOSS SINE คือ swap บทบาท k_in k_out ผ่านการสลับ s เป็น L ลบ s บนฟังก์ชันเดียวกัน ไม่ต้องมีสูตรแยกสำหรับ SPOUT
