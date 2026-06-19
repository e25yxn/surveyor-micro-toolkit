"""Golden tests for smt.wcb."""
import math
from smt import fpmath as fp
from smt import wcb


def test_forward_due_east():
    p = wcb.calculate_forward(20000, 10000, fp.deg_to_rad(90), 519.6152)
    assert math.isclose(p.n, 20000.0, abs_tol=1e-6)
    assert math.isclose(p.e, 10519.6152, abs_tol=1e-6)


def test_inverse_due_east():
    inv = wcb.calculate_inverse(20000, 10000, 20000, 10519.6152)
    assert math.isclose(inv.azimuth, fp.deg_to_rad(90), abs_tol=1e-12)
    assert math.isclose(inv.distance, 519.6152, abs_tol=1e-9)


def test_azimuth_ne():
    az = wcb.calculate_azimuth(0, 0, 100, 100)
    assert math.isclose(az, fp.deg_to_rad(45), abs_tol=1e-12)


def test_forward_inverse_roundtrip():
    n0, e0 = 1537540.123, 587210.456
    az0, d0 = fp.deg_to_rad(123.456), 250.0
    p = wcb.calculate_forward(n0, e0, az0, d0)
    inv = wcb.calculate_inverse(n0, e0, p.n, p.e)
    assert math.isclose(inv.azimuth, az0, abs_tol=1e-12)
    assert math.isclose(inv.distance, d0, abs_tol=1e-9)


def test_offset_point_right_is_south():
    # ไปทางตะวันออก 100 แล้วเยื้องขวา +10 (ขวาของตะวันออก = ใต้)
    p = wcb.calculate_offset_point(0, 0, fp.deg_to_rad(90), 100, 10)
    assert math.isclose(p.n, -10.0, abs_tol=1e-9)
    assert math.isclose(p.e, 100.0, abs_tol=1e-9)
