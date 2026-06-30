Attribute VB_Name = "SMT_Core"
Option Explicit

' ============================================================
' SMT_Core.bas  --  Foundation math for SMT (Surveyor Micro Toolkit)
' Merged from: SMT_FPMath.bas (fpmath.py port) + SMT_WCB.bas (wcb.py port)
'
' Part 1 -- FP-safe angle math (SMT_FPMath):
'   - All angles stored as radians internally
'   - No intermediate rounding; round only at output boundary
'   - All variables declared As Double (never Single)
'   - Sign convention: offset +right/-left; radius +right/-left
'
' Part 2 -- Azimuth / Coordinate Geometry (SMT_WCB):
'   Azimuth (WCB = Whole Circle Bearing):
'   0 = North, increases clockwise: East=pi/2, South=pi, West=3*pi/2
' ============================================================

' ============================================================
' Part 1 -- FP-safe angle math
' ============================================================

Private Function SMT_FloorMod(a As Double, n As Double) As Double
    ' Floor modulo: result is always non-negative, matching Python's (a % n).
    ' VBA's Mod operator converts operands to Long -- unsafe for Double.
    SMT_FloorMod = a - (Int(a / n) * n)
End Function

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
' Expected values (Part 1) -- verified against Python golden data
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

' ============================================================
' Part 2 -- Azimuth / Coordinate Geometry
' ============================================================

Private Function SMT_Atan2(y As Double, x As Double) As Double
    ' Standard atan2(y, x): angle of vector (x,y) from +x axis, range (-pi, pi].
    ' VBA has no built-in atan2; uses Atn() with quadrant correction.
    Dim PI As Double
    PI = SMT_Pi()
    If x > 0# Then
        SMT_Atan2 = Atn(y / x)
    ElseIf x < 0# And y >= 0# Then
        SMT_Atan2 = Atn(y / x) + PI
    ElseIf x < 0# And y < 0# Then
        SMT_Atan2 = Atn(y / x) - PI
    ElseIf x = 0# And y > 0# Then
        SMT_Atan2 = PI / 2#
    ElseIf x = 0# And y < 0# Then
        SMT_Atan2 = -(PI / 2#)
    Else
        SMT_Atan2 = 0#      ' x=0 and y=0: undefined; return 0 (matches Python math.atan2)
    End If
End Function

Public Function SMT_Azimuth(n1 As Double, e1 As Double, _
                             n2 As Double, e2 As Double) As Double
    ' WCB (azimuth) from point1 to point2. Unit: rad out, range [0, 2*pi).
    ' Convention: 0=North, increases clockwise (East=pi/2, South=pi).
    ' Returns 0.0 for coincident points (n1=n2 and e1=e2).
    Dim dN As Double
    Dim dE As Double
    dN = n2 - n1
    dE = e2 - e1
    If dN = 0# And dE = 0# Then
        SMT_Azimuth = 0#
        Exit Function
    End If
    SMT_Azimuth = SMT_NormalizeAngle(SMT_Atan2(dE, dN))
End Function

Public Function SMT_Distance(n1 As Double, e1 As Double, _
                              n2 As Double, e2 As Double) As Double
    ' Horizontal (plan) distance between two points.
    ' Unit: n,e in metres. Returns: plan distance in metres.
    Dim dN As Double
    Dim dE As Double
    dN = n2 - n1
    dE = e2 - e1
    SMT_Distance = Sqr(dN * dN + dE * dE)
End Function

Public Function SMT_CalcForward(n As Double, e As Double, _
                                 az As Double, dist As Double, _
                                 result As String) As Double
    ' Forward calculation: point + azimuth + distance -> one coordinate.
    ' Unit: n,e in metres; az in radians (WCB); dist in metres.
    ' result="N" returns new Northing, result="E" returns new Easting.
    ' Formula: dN = dist*Cos(az),  dE = dist*Sin(az)
    If result = "N" Then
        SMT_CalcForward = n + dist * Cos(az)
    Else
        SMT_CalcForward = e + dist * Sin(az)
    End If
End Function

Public Function SMT_CalcOffset(n As Double, e As Double, _
                                az As Double, dist As Double, _
                                offset As Double, _
                                result As String) As Double
    ' Forward along az by dist, then perpendicular offset.
    ' Unit: n,e in metres; az in radians (WCB); dist,offset in metres.
    ' offset: +right of travel direction, -left of travel direction.
    ' result="N" returns final Northing, result="E" returns final Easting.
    Dim cn As Double
    Dim ce As Double
    Dim offsetAz As Double
    cn = n + dist * Cos(az)
    ce = e + dist * Sin(az)
    If offset <> 0# Then
        ' Perpendicular right = az + pi/2 (clockwise 90 degrees)
        offsetAz = SMT_NormalizeAngle(az + SMT_Pi() / 2#)
        cn = cn + offset * Cos(offsetAz)
        ce = ce + offset * Sin(offsetAz)
    End If
    If result = "N" Then
        SMT_CalcOffset = cn
    Else
        SMT_CalcOffset = ce
    End If
End Function

' ============================================================
' Expected values (Part 2) -- verified against Python golden data
'
'   SMT_Azimuth(0,0, 1,1)                    = 0.7853981633974483  (= pi/4, NE)
'   SMT_Azimuth(0,0, 0,1)                    = 1.5707963267948966  (= pi/2, East)
'   SMT_Azimuth(0,0,-1,0)                    = 3.14159265358979    (= pi, South)
'   SMT_Azimuth(0,0, 0,0)                    = 0.0                 (coincident, guard)
'   SMT_Distance(0,0,3,4)                    = 5.0                 (3-4-5 triangle)
'   SMT_CalcForward(1000,2000,pi/2,100,"N") = 1000.0              (East: no dN)
'   SMT_CalcForward(1000,2000,pi/2,100,"E") = 2100.0              (East: +100 dE)
'   SMT_CalcOffset(1000,2000,0,100,10,"N")  = 1100.0              (North 100m; right 10m: dN unchanged)
'   SMT_CalcOffset(1000,2000,0,100,10,"E")  = 2010.0              (right 10m: E+10)
' ============================================================
