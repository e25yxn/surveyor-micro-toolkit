Attribute VB_Name = "SMT_Geometry"
Option Explicit

' ============================================================
' SMT_Geometry.bas  --  Local/Global coordinate conversion + 3-D rotations
' Merged from: SMT_LocalCoord.bas + SMT_RotX/RotY/RotZ (formerly Part 1
'              of SMT_Rotation3D.bas)
'
' Part 1 -- Local <-> Global coordinate conversion (SMT_LocalCoord):
'   Port and improvement of CHOStoNE / NEtoCHOS (original VBA).
'
'   Local coordinate system:
'     Origin  : (N0, E0) in global grid (metres)
'     X-axis  : points along azimuth AziBEG (survey convention: 0=North, CW+)
'     Chainage: distance along X-axis  (metres, + forward)
'     Offset  : perpendicular distance (+right of travel / -left)
'
'   AziBEG is always received in decimal degrees; converted to radians
'   immediately on entry -- never passed in radians.
'
' Part 2 -- 3-D rotation matrices (SMT_Rotation3D Part 1):
'   Port of professor's original code, 4 fixes applied:
'   (1) Dim i As Long        (was Integer -- overflows > 32767 rows)
'   (2) nRows As Long        (was Integer)
'   (3) Returns new array    (was ByRef -- no longer mutates the caller's data)
'   (4) cosA / sinA computed once before the loop (not inside every iteration)
'
'   Convention: right-hand rule, standard math CCW rotation.
'   RotX(a): Y' =  cosA*Y - sinA*Z,  Z' =  sinA*Y + cosA*Z
'   RotY(a): X' =  cosA*X + sinA*Z,  Z' = -sinA*X + cosA*Z
'   RotZ(a): X' =  cosA*X - sinA*Y,  Y' =  sinA*X + cosA*Y
'   angle_rad is already in radians -- no conversion needed.
'
' Dependency: SMT_Core module must be imported in the same workbook.
' ============================================================

' ============================================================
' Part 1 -- Local <-> Global coordinate conversion
' ============================================================

Private Function SMT_Atan2(y As Double, x As Double) As Double
    ' Standard atan2(y, x) -- standard math convention.
    ' Duplicated here because SMT_Core version is Private (no cross-module access in VBA).
    ' Returns angle of vector (x, y) from +x axis, range (-pi, pi].
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
        SMT_Atan2 = 0#   ' x=0, y=0: undefined; return 0 (matches Python math.atan2)
    End If
End Function

Private Sub SMT_LocalToGlobal(aziBEG_rad As Double, chn As Double, ofs As Double, _
                               ByRef ds As Double, ByRef globalAz As Double)
    ' Converts local (chn, ofs) to polar form in the global frame.
    ' ds       : distance from local origin (metres).
    ' globalAz : survey azimuth of the point from local origin (rad, [0, 2*pi)).
    '
    ' localAz = SMT_Atan2(ofs, chn):
    '   ofs plays the role of "local Easting"  (perpendicular, +right)
    '   chn plays the role of "local Northing" (along AziBEG)
    '   so SMT_Atan2(ofs, chn) = local survey azimuth, matching SMT_Azimuth(dE,dN) convention.
    Dim localAz As Double
    ds = Sqr(chn * chn + ofs * ofs)
    localAz = SMT_Atan2(ofs, chn)                           ' local survey azimuth (rad)
    globalAz = SMT_NormalizeAngle(localAz + aziBEG_rad)     ' rotate to global frame
End Sub

Public Function SMT_LocalToN(n0 As Double, e0 As Double, aziBEG As Double, _
                              chn As Double, ofs As Double) As Double
    ' Northing of the point at local position (chn, ofs).
    ' n0, e0  : global origin (metres).
    ' aziBEG  : azimuth of local X-axis (decimal degrees, survey: 0=North CW+).
    '           Converted to radians immediately.
    ' chn     : chainage along local X-axis (metres, + forward).
    ' ofs     : perpendicular offset (metres, +right / -left).
    ' Returns : Northing (metres) in global grid.
    '
    ' Formula: DS = Sqr(chn^2 + ofs^2)
    '          localAz  = SMT_Atan2(ofs, chn)
    '          globalAz = SMT_NormalizeAngle(localAz + aziBEG_rad)
    '          N = n0 + DS * Cos(globalAz)
    Dim aziBEG_rad As Double
    Dim ds As Double, globalAz As Double
    aziBEG_rad = SMT_DegToRad(aziBEG)   ' degrees -> radians immediately on entry
    SMT_LocalToGlobal aziBEG_rad, chn, ofs, ds, globalAz
    SMT_LocalToN = n0 + ds * Cos(globalAz)
End Function

Public Function SMT_LocalToE(n0 As Double, e0 As Double, aziBEG As Double, _
                              chn As Double, ofs As Double) As Double
    ' Easting of the point at local position (chn, ofs).
    ' n0, e0  : global origin (metres).
    ' aziBEG  : azimuth of local X-axis (decimal degrees, survey: 0=North CW+).
    '           Converted to radians immediately.
    ' chn     : chainage along local X-axis (metres, + forward).
    ' ofs     : perpendicular offset (metres, +right / -left).
    ' Returns : Easting (metres) in global grid.
    '
    ' Formula: DS = Sqr(chn^2 + ofs^2)
    '          localAz  = SMT_Atan2(ofs, chn)
    '          globalAz = SMT_NormalizeAngle(localAz + aziBEG_rad)
    '          E = e0 + DS * Sin(globalAz)
    Dim aziBEG_rad As Double
    Dim ds As Double, globalAz As Double
    aziBEG_rad = SMT_DegToRad(aziBEG)   ' degrees -> radians immediately on entry
    SMT_LocalToGlobal aziBEG_rad, chn, ofs, ds, globalAz
    SMT_LocalToE = e0 + ds * Sin(globalAz)
End Function

Public Function SMT_GlobalToY(n0 As Double, e0 As Double, aziBEG As Double, _
                                 n As Double, e As Double) As Double
    ' Chainage of a global point (n, e) in the local coordinate system.
    ' n0, e0  : global origin (metres).
    ' aziBEG  : azimuth of local X-axis (decimal degrees, survey: 0=North CW+).
    '           Converted to radians immediately.
    ' n, e    : global Northing and Easting of the target point (metres).
    ' Returns : chainage (metres) -- projection of (n-n0, e-e0) onto AziBEG axis.
    '
    ' Formula: dN = n - n0,  dE = e - e0
    '          Chn = dN*Cos(aziBEG_rad) + dE*Sin(aziBEG_rad)
    Dim aziBEG_rad As Double
    Dim dN As Double, dE As Double
    aziBEG_rad = SMT_DegToRad(aziBEG)   ' degrees -> radians immediately on entry
    dN = n - n0
    dE = e - e0
    SMT_GlobalToY = dN * Cos(aziBEG_rad) + dE * Sin(aziBEG_rad)
End Function

Public Function SMT_GlobalToX(n0 As Double, e0 As Double, aziBEG As Double, _
                                 n As Double, e As Double) As Double
    ' Perpendicular offset of a global point (n, e) from the local X-axis.
    ' n0, e0  : global origin (metres).
    ' aziBEG  : azimuth of local X-axis (decimal degrees, survey: 0=North CW+).
    '           Converted to radians immediately.
    ' n, e    : global Northing and Easting of the target point (metres).
    ' Returns : offset (metres, +right of AziBEG / -left).
    '           Positive = point is to the right of the local X-axis (clockwise from AziBEG).
    '           Negative = point is to the left.
    '
    ' Formula: dN = n - n0,  dE = e - e0
    '          Ofs = -dN*Sin(aziBEG_rad) + dE*Cos(aziBEG_rad)
    Dim aziBEG_rad As Double
    Dim dN As Double, dE As Double
    aziBEG_rad = SMT_DegToRad(aziBEG)   ' degrees -> radians immediately on entry
    dN = n - n0
    dE = e - e0
    SMT_GlobalToX = -dN * Sin(aziBEG_rad) + dE * Cos(aziBEG_rad)
End Function

' ============================================================
' Expected values (Part 1) -- verified against Python
' Origin = (N0=1000, E0=2000), AziBEG = 90 deg (pointing East)
'
'   SMT_LocalToN(1000, 2000, 90, 100,  0) = 1000.0
'     DS=100, localAz=0, globalAz=pi/2 -> N = 1000 + 100*cos(pi/2) = 1000
'
'   SMT_LocalToE(1000, 2000, 90, 100,  0) = 2100.0
'     DS=100, localAz=0, globalAz=pi/2 -> E = 2000 + 100*sin(pi/2) = 2100
'
'   SMT_LocalToN(1000, 2000, 90,   0, 50) = 950.0
'     DS=50, localAz=pi/2, globalAz=pi -> N = 1000 + 50*cos(pi) = 950
'     (offset +50 right of East = South when aziBEG=90)
'
'   SMT_GlobalToY(1000, 2000, 90, 1000, 2100) = 100.0
'     dN=0, dE=100 -> Chn = 0*cos(pi/2) + 100*sin(pi/2) = 100
'
'   SMT_GlobalToX(1000, 2000, 90,  950, 2000) =  50.0
'     dN=-50, dE=0 -> Ofs = -(-50)*sin(pi/2) + 0*cos(pi/2) = 50
' ============================================================

' ============================================================
' Part 2 -- 3-D rotation functions
' pts : 1-based Variant array, n rows x 3 cols (col1=X, col2=Y, col3=Z).
' angle_rad : rotation angle in radians (positive = CCW when viewed along +axis).
' Returns  : new Variant array same size as pts; original is NOT modified.
' ============================================================

Public Function SMT_RotX(pts As Variant, angle_rad As Double) As Variant
    ' Rotation around the X-axis by angle_rad (radians).
    ' X is unchanged; Y and Z rotate in the YZ plane.
    ' Y' =  cos(a)*Y - sin(a)*Z
    ' Z' =  sin(a)*Y + cos(a)*Z
    Dim nRows As Long, i As Long
    Dim cosA As Double, sinA As Double
    Dim result() As Double
    nRows = UBound(pts, 1)
    ReDim result(1 To nRows, 1 To 3)
    cosA = Cos(angle_rad)    ' computed once -- not inside the loop
    sinA = Sin(angle_rad)
    For i = 1 To nRows
        result(i, 1) = pts(i, 1)                              ' X unchanged
        result(i, 2) = cosA * pts(i, 2) - sinA * pts(i, 3)   ' Y'
        result(i, 3) = sinA * pts(i, 2) + cosA * pts(i, 3)   ' Z'
    Next i
    SMT_RotX = result
End Function

Public Function SMT_RotY(pts As Variant, angle_rad As Double) As Variant
    ' Rotation around the Y-axis by angle_rad (radians).
    ' Y is unchanged; X and Z rotate in the XZ plane.
    ' X' =  cos(a)*X + sin(a)*Z
    ' Z' = -sin(a)*X + cos(a)*Z
    Dim nRows As Long, i As Long
    Dim cosA As Double, sinA As Double
    Dim result() As Double
    nRows = UBound(pts, 1)
    ReDim result(1 To nRows, 1 To 3)
    cosA = Cos(angle_rad)
    sinA = Sin(angle_rad)
    For i = 1 To nRows
        result(i, 1) = cosA * pts(i, 1) + sinA * pts(i, 3)   ' X'
        result(i, 2) = pts(i, 2)                              ' Y unchanged
        result(i, 3) = -sinA * pts(i, 1) + cosA * pts(i, 3)  ' Z'
    Next i
    SMT_RotY = result
End Function

Public Function SMT_RotZ(pts As Variant, angle_rad As Double) As Variant
    ' Rotation around the Z-axis by angle_rad (radians).
    ' Z is unchanged; X and Y rotate in the XY plane.
    ' X' =  cos(a)*X - sin(a)*Y
    ' Y' =  sin(a)*X + cos(a)*Y
    Dim nRows As Long, i As Long
    Dim cosA As Double, sinA As Double
    Dim result() As Double
    nRows = UBound(pts, 1)
    ReDim result(1 To nRows, 1 To 3)
    cosA = Cos(angle_rad)
    sinA = Sin(angle_rad)
    For i = 1 To nRows
        result(i, 1) = cosA * pts(i, 1) - sinA * pts(i, 2)   ' X'
        result(i, 2) = sinA * pts(i, 1) + cosA * pts(i, 2)   ' Y'
        result(i, 3) = pts(i, 3)                              ' Z unchanged
    Next i
    SMT_RotZ = result
End Function

' ============================================================
' Expected values (Part 2) -- verified against Python / manual calculation
' angle_rad = pi/2 = 90 deg;  pts = [[1, 0, 0]]  (1-row, 3-col, 1-based)
'
'   SMT_RotZ(pts, pi/2)(1,1) = 0.0   X' = cos(90)*1 - sin(90)*0 = 0
'   SMT_RotZ(pts, pi/2)(1,2) = 1.0   Y' = sin(90)*1 + cos(90)*0 = 1
'   SMT_RotZ(pts, pi/2)(1,3) = 0.0   Z' = Z = 0
'   Result point: (0, 1, 0)  -- (1,0,0) rotated 90 deg CCW around Z-axis
'
'   SMT_RotX(pts, pi/2)(1,1) = 1.0   X' = X = 1
'   SMT_RotX(pts, pi/2)(1,2) = 0.0   Y' = cos(90)*0 - sin(90)*0 = 0
'   SMT_RotX(pts, pi/2)(1,3) = 0.0   Z' = sin(90)*0 + cos(90)*0 = 0
'   (X-axis point is unchanged by RotX, as expected)
' ============================================================
