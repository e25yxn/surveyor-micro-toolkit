"""Golden tests for smt.fpmath (ค่ารู้คำตอบ + เทียบ oracle)."""
import math

import pytest

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


# ---------------------------------------------------------------------------
# round_to \u2014 inf / nan guards
# ---------------------------------------------------------------------------

def test_round_to_inf():
    assert math.isinf(fp.round_to(math.inf, 2))
    assert fp.round_to(math.inf, 2) > 0


def test_round_to_nan():
    assert math.isnan(fp.round_to(math.nan, 2))


# ---------------------------------------------------------------------------
# trunc_to \u2014 decimals=0, inf, nan
# ---------------------------------------------------------------------------

def test_trunc_zero_decimals():
    assert fp.trunc_to(3.987, 0) == 3.0
    assert fp.trunc_to(-3.987, 0) == -3.0


def test_trunc_inf():
    assert math.isinf(fp.trunc_to(math.inf, 2))


def test_trunc_nan():
    assert math.isnan(fp.trunc_to(math.nan, 2))


# ---------------------------------------------------------------------------
# is_almost_equal \u2014 absolute branch, relative branch, boundary
# ---------------------------------------------------------------------------

def test_is_almost_equal_exact():
    assert fp.is_almost_equal(1.5, 1.5) is True


def test_is_almost_equal_large_numbers_relative():
    # diff=1e-6 > eps; relative: 1e-6 <= 1e-9 * 1e6 = 1e-3 \u2192 True
    assert fp.is_almost_equal(1_000_000.0, 1_000_000.0 + 1e-6) is True


def test_is_almost_equal_a_zero_b_tiny():
    # diff=1e-15 <= eps(1e-9) \u2192 True (absolute branch)
    assert fp.is_almost_equal(0.0, 1e-15) is True


def test_is_almost_equal_one_zero_large_other():
    # diff=1.0 > eps; relative: 1.0 <= 1e-9 * 1 = 1e-9 \u2192 False
    assert fp.is_almost_equal(0.0, 1.0) is False


# ---------------------------------------------------------------------------
# is_in_range \u2014 inverted range, single-point range
# ---------------------------------------------------------------------------

def test_is_in_range_lo_gt_hi():
    assert fp.is_in_range(3.0, 5.0, 1.0) is False


def test_is_in_range_point_range():
    assert fp.is_in_range(5.0, 5.0, 5.0) is True
    assert fp.is_in_range(5.1, 5.0, 5.0) is False


# ---------------------------------------------------------------------------
# floor_mod \u2014 n=0 (ZeroDivisionError), n<0, fractional n
# ---------------------------------------------------------------------------

def test_floor_mod_n_zero():
    with pytest.raises(ZeroDivisionError):
        fp.floor_mod(5.0, 0)


def test_floor_mod_n_negative():
    result = fp.floor_mod(3, -4)
    assert -4 < result <= 0


def test_floor_mod_fractional_n():
    assert math.isclose(fp.floor_mod(1.5, 1.0), 0.5, abs_tol=1e-12)


# ---------------------------------------------------------------------------
# normalize_angle \u2014 0 and 2\u03c0 boundary
# ---------------------------------------------------------------------------

def test_normalize_angle_zero():
    assert fp.normalize_angle(0.0) == 0.0


def test_normalize_angle_two_pi():
    assert math.isclose(fp.normalize_angle(fp.TWO_PI), 0.0, abs_tol=1e-12)


# ---------------------------------------------------------------------------
# calculate_angle_diff \u2014 a==b, |diff|=\u03c0, diff=2\u03c0
# ---------------------------------------------------------------------------

def test_angle_diff_same():
    for a in (0.0, 1.0, math.pi, fp.TWO_PI):
        assert math.isclose(fp.calculate_angle_diff(a, a), 0.0, abs_tol=1e-12)


def test_angle_diff_pi_exactly():
    result = fp.calculate_angle_diff(math.pi, 0.0)
    assert math.isclose(abs(result), math.pi, abs_tol=1e-12)


def test_angle_diff_two_pi_apart():
    assert math.isclose(fp.calculate_angle_diff(fp.TWO_PI, 0.0), 0.0, abs_tol=1e-12)


# ---------------------------------------------------------------------------
# kahan_sum \u2014 empty list, single element, negative, mixed sign
# ---------------------------------------------------------------------------

def test_kahan_sum_empty():
    assert fp.kahan_sum([]) == 0.0


def test_kahan_sum_single():
    assert fp.kahan_sum([42.0]) == 42.0


def test_kahan_sum_negative():
    assert math.isclose(fp.kahan_sum([-0.1] * 10), -1.0, abs_tol=1e-12)


def test_kahan_sum_mixed_sign():
    assert fp.kahan_sum([1.0, -1.0, 1.0, -1.0]) == 0.0


# ---------------------------------------------------------------------------
# deg_to_rad / rad_to_deg \u2014 zero, negative, >360\u00b0
# ---------------------------------------------------------------------------

def test_deg_to_rad_zero():
    assert fp.deg_to_rad(0.0) == 0.0


def test_deg_to_rad_negative():
    assert math.isclose(fp.deg_to_rad(-90.0), -math.pi / 2, abs_tol=1e-12)


def test_deg_to_rad_over_360():
    assert math.isclose(fp.deg_to_rad(540.0), 3 * math.pi, abs_tol=1e-12)


def test_rad_to_deg_zero():
    assert fp.rad_to_deg(0.0) == 0.0


def test_rad_to_deg_negative():
    assert math.isclose(fp.rad_to_deg(-math.pi / 2), -90.0, abs_tol=1e-12)


def test_rad_to_deg_over_two_pi():
    assert math.isclose(fp.rad_to_deg(3 * math.pi), 540.0, abs_tol=1e-12)


# ---------------------------------------------------------------------------
# packed_dms_to_rad \u2014 zero, negative
# ---------------------------------------------------------------------------

def test_packed_dms_zero():
    assert fp.packed_dms_to_rad(0.0) == 0.0


def test_packed_dms_negative():
    pos = fp.packed_dms_to_rad(120.012256)
    neg = fp.packed_dms_to_rad(-120.012256)
    assert math.isclose(neg, -pos, abs_tol=1e-12)


# ---------------------------------------------------------------------------
# rad_to_packed_dms \u2014 zero, negative, seconds carry
# ---------------------------------------------------------------------------

def test_rad_to_packed_dms_zero():
    assert fp.rad_to_packed_dms(0.0) == 0.0


def test_rad_to_packed_dms_negative():
    assert math.isclose(fp.rad_to_packed_dms(-math.pi / 2), -90.0, abs_tol=1e-6)


def test_rad_to_packed_dms_carry():
    # 0\u00b059'59.997": s rounds to 60.00 \u2192 carry \u2192 1\u00b000'00.00" = 1.0000
    rad = fp.dms_to_rad(0, 59, 59.997)
    result = fp.rad_to_packed_dms(rad)
    assert math.isclose(result, 1.0, abs_tol=1e-4)


# ---------------------------------------------------------------------------
# rad_to_dms_string \u2014 zero, negative, sec_decimals=0
# ---------------------------------------------------------------------------

def test_dms_string_zero():
    s = fp.rad_to_dms_string(0.0)
    assert s.startswith('0\u00b0')


def test_dms_string_negative():
    s = fp.rad_to_dms_string(-math.pi / 2)
    assert s.startswith('-')
    assert '90' in s


def test_dms_string_sec_decimals_zero():
    rad = fp.deg_to_rad(120.0 + 1 / 60.0 + 22.0 / 3600.0)
    s = fp.rad_to_dms_string(rad, sec_decimals=0)
    assert '.' not in s


# ---------------------------------------------------------------------------
# dms_to_rad \u2014 negative d, all zero, minutes-only
# ---------------------------------------------------------------------------

def test_dms_to_rad_negative_d():
    assert math.isclose(fp.dms_to_rad(-90, 0, 0), -math.pi / 2, abs_tol=1e-12)


def test_dms_to_rad_zero():
    assert fp.dms_to_rad(0, 0, 0) == 0.0


def test_dms_to_rad_only_minutes():
    # 0\u00b030'0" = 0.5\u00b0 = \u03c0/360
    assert math.isclose(fp.dms_to_rad(0, 30, 0), math.pi / 360, abs_tol=1e-12)
