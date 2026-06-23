"""Golden tests for smt.fpmath (ค่ารู้คำตอบ + เทียบ oracle)."""
import math
from smt import fpmath as fp


def test_conversions():
    assert math.isclose(fp.deg_to_rad(180), math.pi, abs_tol=1e-12)
    assert math.isclose(fp.rad_to_deg(math.pi), 180.0, abs_tol=1e-12)


def test_normalize_angle():
    assert math.isclose(fp.normalize_angle(-0.1), fp.TWO_PI - 0.1, abs_tol=1e-12)
    assert math.isclose(fp.normalize_angle(fp.TWO_PI + 0.1), 0.1, abs_tol=1e-12)


def test_angle_diff_wrap():
    # 10 deg - 350 deg ควรได้ +20 deg (ทางสั้น) ไม่ใช่ -340
    got = fp.calculate_angle_diff(fp.deg_to_rad(10), fp.deg_to_rad(350))
    assert math.isclose(got, fp.deg_to_rad(20), abs_tol=1e-12)


def test_round_half_away():
    assert fp.round_to(1.005, 2) == 1.01       # บั๊กคลาสสิกต้องไม่เกิด
    assert fp.round_to(2.5, 0) == 3.0
    assert fp.round_to(-2.5, 0) == -3.0
    assert fp.round_to(2.34567, 3) == 2.346


def test_trunc():
    assert fp.trunc_to(1.999, 2) == 1.99
    assert fp.trunc_to(-1.999, 2) == -1.99


def test_compare():
    assert fp.is_almost_equal(0.1 + 0.2, 0.3) is True
    assert fp.is_in_range(10.00005, 0, 10, 1e-4) is True
    assert fp.is_in_range(11, 0, 10) is False


def test_floor_mod_positive():
    assert fp.floor_mod(-1, 4) == 3


def test_kahan_sum():
    assert math.isclose(fp.kahan_sum([0.1] * 10), 1.0, abs_tol=1e-12)


def test_dms_roundtrip():
    deg = 120 + 1 / 60 + 22.56 / 3600
    rad = fp.deg_to_rad(deg)
    assert math.isclose(fp.rad_to_packed_dms(rad), 120.012256, abs_tol=1e-6)
    assert math.isclose(fp.packed_dms_to_rad(120.012256), rad, abs_tol=1e-9)
    assert fp.rad_to_dms_string(rad) == "120\u00b001\u203222.56\u2033"
    assert math.isclose(fp.dms_to_rad(120, 1, 22.56), rad, abs_tol=1e-12)
