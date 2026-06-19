"""wcb - Azimuth / Coordinate Geometry (Foundation layer).

พอร์ตจาก reference/WCB.gs

Azimuth (WCB = Whole Circle Bearing): เริ่ม 0 ที่ทิศเหนือ วนขวาตามเข็มนาฬิกา
    เหนือ=0, ตะวันออก=90, ใต้=180, ตะวันตก=270 (องศา)

เทียบ Casio fx-5800p:
    calculate_inverse ~ Pol(dN, dE)   (สองจุด -> มุม + ระยะ)
    calculate_forward ~ Rec(d, az)    (มุม + ระยะ -> พิกัด)

หน่วยมุมภายใน = radian
การตั้งชื่อ: ดู docs/naming_convention.md
"""
from __future__ import annotations

import math
from typing import NamedTuple

from . import fpmath


class Point(NamedTuple):
    """พิกัดราบ (Northing, Easting)."""
    n: float
    e: float


class Inverse(NamedTuple):
    """ผลการคำนวณย้อน: azimuth (radian) + ระยะราบ."""
    azimuth: float
    distance: float


def calculate_azimuth(n1: float, e1: float, n2: float, e2: float) -> float:
    """azimuth (radian) จากจุด1 ไปจุด2, วัดจากเหนือวนขวา, ช่วง [0, 2*pi).

    ใช้ atan2(dE, dN) ไม่ใช่ atan2(dN, dE).
    """
    az = math.atan2(e2 - e1, n2 - n1)
    return fpmath.normalize_angle(az)


def calculate_distance_2d(n1: float, e1: float, n2: float, e2: float) -> float:
    """ระยะราบระหว่างสองจุด (ใช้ math.hypot กัน overflow/underflow)."""
    return math.hypot(n2 - n1, e2 - e1)


def calculate_distance_3d(n1: float, e1: float, z1: float,
                          n2: float, e2: float, z2: float) -> float:
    """ระยะตรง (slope distance) รวมความต่างระดับ."""
    return math.hypot(n2 - n1, e2 - e1, z2 - z1)


def calculate_forward(n1: float, e1: float, azimuth: float, distance: float) -> Point:
    """จุดตั้ง + azimuth(radian) + ระยะ -> จุดใหม่.

    dN = d*cos(az), dE = d*sin(az)  (เทียบ Casio: Rec(distance, azimuth)).
    """
    return Point(
        n=n1 + distance * math.cos(azimuth),
        e=e1 + distance * math.sin(azimuth),
    )


def calculate_inverse(n1: float, e1: float, n2: float, e2: float) -> Inverse:
    """สองจุด -> azimuth(radian) + ระยะ (เทียบ Casio: Pol)."""
    return Inverse(
        azimuth=calculate_azimuth(n1, e1, n2, e2),
        distance=calculate_distance_2d(n1, e1, n2, e2),
    )


def calculate_offset_point(n1: float, e1: float, azimuth: float,
                           along: float, offset: float = 0.0) -> Point:
    """เดินตาม azimuth เป็นระยะ along แล้วเยื้องตั้งฉาก offset.

    offset: + = ขวามือของทิศเดิน, - = ซ้ายมือ. ขวามือ = azimuth + 90 องศา.
    """
    cl = calculate_forward(n1, e1, azimuth, along)
    if not offset:
        return cl
    off_az = fpmath.normalize_angle(azimuth + math.pi / 2.0)
    return calculate_forward(cl.n, cl.e, off_az, offset)
