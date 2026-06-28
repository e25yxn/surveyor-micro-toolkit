# Plan Part 2 — Overlap Check Report
วันที่: 2026-06-28

---

## 1. หมายเหตุเบื้องต้น

`session_logs/plan.md` **ไม่มีอยู่จริง** — ไม่ถูกสร้างไว้ในเซสชันก่อน  
แต่ scope ของ Part 2 สามารถสืบค้นได้จากสองแหล่ง:

- `review_logs/04_coverage_docstring.txt` — Coverage Audit ที่ระบุ ⚠️ gaps ครบทุกไฟล์  
- `session_logs/latest.md` บรรทัด: "Part 2 (vertical, crossfall, surface, check, builders) รอ session ถัดไป"

---

## 2. Scope ของ Part 2 (สรุปจาก Coverage Audit)

| ไฟล์ | Edge case ที่ยังขาด | ประมาณ test |
|------|---------------------|-------------|
| vertical.py | grade asymmetric arm boundary, empty segs, parse header-only/NaN-sta/empty-lvc/short-row | ~6 |
| crossfall.py | parse NaN sta_start, short row → default type V | ~2 |
| surface.py | calculate_point_3d: ValueError propagated from alignment | ~1 |
| check.py | empty controls → [], empty vchecks → [], ValueError path (horizontal + vertical) | ~4-5 |
| alignment_builder.py | issues: spiral overflow (delta_circular<0), compound sum>turn, Ls=0; check_against_drawing: empty controls, name-not-found | ~5 |
| vertical_builder.py | L=0 VPI (no VC), multiple overlaps, degenerate; build_table: empty input; check_against_drawing: empty, name-not-found | ~6 |
| **รวม** | | **~25-26 tests** |

---

## 3. TestNoCurvePI — 12 tests ที่เพิ่งเพิ่ม (commit cdf896d)

ทั้งหมดอยู่ใน `tests/builders/test_alignment_builder.py` คลาส `TestNoCurvePI`  
จัดกลุ่มได้เป็น 9 กลุ่ม:

| กลุ่ม | ชื่อ test | สิ่งที่ทดสอบ |
|-------|-----------|--------------|
| TA | test_angle_point_element_types | no-R vertex → elements = [T, T] |
| TA | test_angle_point_control_names | control names = [BP, IP, EP] |
| TB | test_angle_point_ip_station_and_coords | IP station + N/E ถูกต้อง |
| TC | test_r_zero_is_angle_point | R=0 → treated as angle point |
| TD | test_collinear_pi_no_error | collinear PI ไม่ raise, station ถูก |
| TE | test_angle_point_no_issues | issues == [] สำหรับ angle point สะอาด |
| TF | test_curve_then_angle_point_types | mixed C+IP: element types ถูก |
| TF | test_curve_then_angle_point_ip_station | IP station หลัง arc ถูกต้อง |
| TG | test_angle_point_then_curve_types | IP+C: element types ถูก |
| TG | test_angle_point_then_curve_pc_position | PC position หลัง IP ถูก |
| TH | test_two_consecutive_angle_points | IP+IP: 3 tangents, 2 IPs |
| TI | test_chain_continuity_with_angle_point | chain continuity ผ่าน IP |

---

## 4. ผลการตรวจ Overlap

### ไม่มี overlap ใดๆ ระหว่าง TestNoCurvePI กับ Part 2

**เหตุผลหลัก:**

**TestNoCurvePI** ทดสอบ **EXT-001 feature** (no-curve PI / angle point):
- เน้นว่า vertex ที่ไม่มี R ทำงานถูกต้อง (element type, control name, station, coordinates)
- เป็น "happy path + structural" ของ feature ใหม่

**Part 2** ทดสอบ **edge cases / error paths** ของ modules ที่มีอยู่แล้ว:
- vertical, crossfall, surface: parse edge cases + None return condition
- check.py: empty input + ValueError path
- alignment_builder: **issues (error detection)** — spiral too long, compound overflow, Ls=0
- vertical_builder: overlap detection, degenerate VPI, empty input

### จุดที่อาจดูเหมือนซ้อนกัน แต่ไม่ใช่

| TestNoCurvePI | Part 2 alignment_builder | ความสัมพันธ์ |
|---------------|--------------------------|--------------|
| TE: `r.issues == []` สำหรับ angle point | issues != [] สำหรับ spiral overflow | **คนละ scenario** — TE ยืนยัน no error, Part 2 ยืนยัน WITH error |
| TI: chain continuity loop (calculate_exit_state) | check.py check_horizontal/check_vertical | **คนละฟังก์ชัน** — TI ไม่เรียก check.py เลย |

---

## 5. สรุป

**แผน Part 2 ใช้ได้ทั้งหมด — ไม่มี test ใดที่ต้องตัดหรือปรับ**

- TestNoCurvePI (12 tests) ครอบ EXT-001 feature ทั้งหมดในมิติ structural/happy-path
- Part 2 (~26 tests) ครอบ error paths + edge cases ที่ Coverage Audit ระบุว่ายังขาด
- ทั้งสองชุด **complement กัน ไม่ conflict กัน**

**ข้อแนะนำ:** สร้าง `session_logs/plan.md` ใหม่ก่อนเริ่ม Part 2 ตาม Process ส่วนที่ 3 (Plan-Review-Approve)
