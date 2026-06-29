Attribute VB_Name = "SMT_FPMath"
Option Explicit

' ============================================================
' SMT_FPMath.bas  --  VBA port of src/smt/fpmath.py
' SMT (Surveyor Micro Toolkit) -- Foundation FP-safe angle math
'
' Rules:
'   - All angles stored as radians internally
'   - No intermediate rounding; round only at output boundary
'   - All variables declared As Double (never Single)
'   - Sign convention: offset +right/-left; radius +right/-left
' ============================================================

' ============================================================
' Private helper -- not exposed to worksheet or caller
' ============================================================

Private Function SMT_FloorMod(a As Double, n As Double) As Double
    ' Floor modulo: result is always non-negative, matching Python's (a % n).
    ' VBA's Mod operator converts operands to Long -- unsafe for Double.
    SMT_FloorMod = a - (Int(a / n) * n)
End Function

' ============================================================
' Public API -- 5 functions, all with SMT_ prefix
' ============================================================

Public Function SMT_Pi() As Double
    ' Returns pi to full IEEE 754 Double precision (~15 significant digits).
    ' Unit: dimensionless constant.
    SMT_Pi = 4# * Atn(1#)
End Function

Public Function SMT_DegToRad(deg As Double) As Double
    ' Converts decimal degrees to radians.
    ' Unit: deg in --> rad out. No intermediate rounding.
    SMT_DegToRad = deg * (SMT_Pi() / 180#)
End Function

Public Function SMT_RadToDeg(rad As Double) As Double
    ' Converts radians to decimal degrees.
    ' Unit: rad in --> deg out. No intermediate rounding.
    SMT_RadToDeg = rad * (180# / SMT_Pi())
End Function

Public Function SMT_NormalizeAngle(az As Double) As Double
    ' Normalizes angle to [0, 2*pi). Unit: rad in --> rad out.
    ' Wraps any radian value into the half-open interval [0, 2*pi)
    ' using floor-mod (safe for negative inputs).
    Dim TWO_PI As Double
    TWO_PI = 2# * SMT_Pi()
    SMT_NormalizeAngle = SMT_FloorMod(az, TWO_PI)
End Function

Public Function SMT_AngleDiff(a As Double, b As Double) As Double
    ' Shortest signed difference (a - b) in (-pi, pi].
    ' Unit: rad in --> rad out.
    ' Sign: positive = a is CCW of b; negative = a is CW of b.
    ' Formula: floor_mod(a - b + pi, 2*pi) - pi  (mirrors Python oracle).
    Dim PI As Double
    Dim TWO_PI As Double
    PI = SMT_Pi()
    TWO_PI = 2# * PI
    SMT_AngleDiff = SMT_FloorMod(a - b + PI, TWO_PI) - PI
End Function

' ============================================================
' Expected values -- verified against Python golden data
'
'   SMT_Pi()                     = 3.14159265358979  (IEEE 754 Double)
'   SMT_DegToRad(90)             = 1.5707963267948966
'   SMT_DegToRad(180)            = 3.14159265358979
'   SMT_RadToDeg(SMT_Pi())       = 180.0
'   SMT_NormalizeAngle(-0.1)     = 6.18318530717959  (= 2*pi - 0.1)
'   SMT_NormalizeAngle(6.3)      = 0.01681469282041  (= 6.3 - 2*pi)
'   SMT_AngleDiff(0.1, 6.2)      = 0.18318530717959  (CCW, shortest)
'   SMT_AngleDiff(6.2, 0.1)      =-0.18318530717959  (CW, shortest)
' ============================================================
