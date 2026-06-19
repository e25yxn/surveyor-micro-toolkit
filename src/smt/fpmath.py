"""fpmath - FP-safe math utilities (Foundation layer / ชั้นล่างสุด).

พอร์ตจาก reference/FPMath.gs (engine ที่ผ่าน AllTests 45/45)

ปรัชญา (SAFE + SMALL + STABLE):
    1) คำนวณด้วย full IEEE 754 (float) เสมอ -- ห้ามปัดเศษกลางทาง
    2) ปัดเศษเฉพาะตอนส่งออก/แสดงผล
    3) ทุกฟังก์ชันเป็น pure function

หน่วยมาตรฐานภายใน engine:
    - มุม (angle) : radian
    - เก็บ/แสดงมุม: packed DMS เช่น 120.012256 = 120 deg 01' 22.56"

การตั้งชื่อ: ดู docs/naming_convention.md
"""
from __future__ import annotations

import math
from decimal import Decimal, ROUND_HALF_UP, ROUND_DOWN

EPS: float = 1e-9                 # tolerance เริ่มต้นสำหรับเทียบ float
TWO_PI: float = 2.0 * math.pi
DEG2RAD: float = math.pi / 180.0
RAD2DEG: float = 180.0 / math.pi


# --------------------------------------------------------------------------
# ROUNDING -- ใช้ตอนส่งออกเท่านั้น
# --------------------------------------------------------------------------
def round_to(value: float, decimals: int = 3) -> float:
    """ปัดเศษแบบ round-half-away-from-zero (2.5 -> 3, -2.5 -> -3).

    ใช้ Decimal(repr(value)) เพื่อเลี่ยงบั๊ก 1.005 -> 1.00 (เทียบเท่าเทคนิค
    exponential-string ในต้นฉบับ JS).
    """
    if not math.isfinite(value):
        return value
    quantum = Decimal(1).scaleb(-decimals)
    return float(Decimal(repr(value)).quantize(quantum, rounding=ROUND_HALF_UP))


def trunc_to(value: float, decimals: int = 3) -> float:
    """ตัดทศนิยมทิ้ง (ไม่ปัด) -- ใช้กับการแสดง STATION."""
    if not math.isfinite(value):
        return value
    quantum = Decimal(1).scaleb(-decimals)
    return float(Decimal(repr(value)).quantize(quantum, rounding=ROUND_DOWN))


# --------------------------------------------------------------------------
# COMPARISON -- เทียบ float อย่างปลอดภัย
# --------------------------------------------------------------------------
def is_almost_equal(a: float, b: float, eps: float = EPS) -> bool:
    """a ~ b หรือไม่ (ผสม absolute + relative tolerance)."""
    diff = abs(a - b)
    if diff <= eps:
        return True
    return diff <= eps * max(abs(a), abs(b))


def is_in_range(value: float, lo: float, hi: float, eps: float = EPS) -> bool:
    """value อยู่ในช่วง [lo, hi] ไหม (เผื่อ tolerance ที่ขอบ)."""
    return (value >= (lo - eps)) and (value <= (hi + eps))


# --------------------------------------------------------------------------
# MODULAR / ANGLE
# --------------------------------------------------------------------------
def floor_mod(a: float, n: float) -> float:
    """modulo ที่ผลลัพธ์เป็นบวกเสมอ: floor_mod(-1, 4) = 3."""
    return ((a % n) + n) % n


def normalize_angle(rad: float) -> float:
    """บีบมุม (radian) ให้อยู่ในช่วง [0, 2*pi)."""
    return floor_mod(rad, TWO_PI)


def angle_diff(a: float, b: float) -> float:
    """ผลต่างมุมที่สั้นที่สุด (a - b) ในช่วง (-pi, pi]."""
    return floor_mod(a - b + math.pi, TWO_PI) - math.pi


# --------------------------------------------------------------------------
# SAFE ARITHMETIC -- ลดการสะสมความคลาด (Error Propagation)
# --------------------------------------------------------------------------
def kahan_sum(values: list[float]) -> float:
    """Kahan summation -- บวกเลขชุดยาวโดยชดเชย round-off."""
    total = 0.0
    comp = 0.0
    for v in values:
        y = v - comp
        t = total + y
        comp = (t - total) - y
        total = t
    return total


# --------------------------------------------------------------------------
# CONVERSION -- แปลงหน่วยมุม (idiom <source>_to_<target>)
# --------------------------------------------------------------------------
def deg_to_rad(deg: float) -> float:
    return deg * DEG2RAD


def rad_to_deg(rad: float) -> float:
    return rad * RAD2DEG


def packed_dms_to_rad(packed: float, sec_decimals: int = 4) -> float:
    """packed DMS (D.MMSSsss) -> radian. เช่น 120.012256 -> rad ของ 120 01' 22.56"."""
    sign = -1.0 if packed < 0 else 1.0
    a = abs(packed)
    d = math.trunc(a)
    r1 = round_to((a - d) * 100.0, sec_decimals + 2)   # .MMSSsss -> MM.SSsss
    m = math.trunc(r1)
    s = round_to((r1 - m) * 100.0, sec_decimals)        # .SSsss -> SS.sss
    decimal_deg = d + m / 60.0 + s / 3600.0
    return sign * decimal_deg * DEG2RAD


def rad_to_packed_dms(rad: float, sec_decimals: int = 2) -> float:
    """radian -> packed DMS (D.MMSSsss). ปัดวินาทีแล้วทดเมื่อถึง 60."""
    deg = rad * RAD2DEG
    sign = -1.0 if deg < 0 else 1.0
    deg = abs(deg)
    d = math.trunc(deg)
    m_full = (deg - d) * 60.0
    m = math.trunc(m_full)
    s = round_to((m_full - m) * 60.0, sec_decimals)
    if s >= 60:
        s -= 60
        m += 1
    if m >= 60:
        m -= 60
        d += 1
    packed = d + m / 100.0 + s / 10000.0
    return sign * round_to(packed, sec_decimals + 4)


def rad_to_dms_string(rad: float, sec_decimals: int = 2) -> str:
    """radian -> ข้อความ DMS เช่น \"120\u00b001\u203222.56\u2033\"."""
    deg = rad * RAD2DEG
    sign = "-" if deg < 0 else ""
    deg = abs(deg)
    d = math.trunc(deg)
    m_full = (deg - d) * 60.0
    m = math.trunc(m_full)
    s = round_to((m_full - m) * 60.0, sec_decimals)
    if s >= 60:
        s -= 60
        m += 1
    if m >= 60:
        m -= 60
        d += 1
    ss = f"{s:.{sec_decimals}f}"
    if s < 10:
        ss = "0" + ss
    mm = f"{m:02d}"
    return f"{sign}{d}\u00b0{mm}\u2032{ss}\u2033"


def dms_to_rad(d: float, m: float = 0.0, s: float = 0.0) -> float:
    """องค์ประกอบ D, M, S -> radian."""
    sign = -1.0 if d < 0 else 1.0
    decimal_deg = abs(d) + m / 60.0 + s / 3600.0
    return sign * decimal_deg * DEG2RAD
