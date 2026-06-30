Attribute VB_Name = "SMT_LocalCoord"
Option Explicit

' ============================================================
' SMT_LocalCoord.bas  --  Local <-> Global coordinate conversion
' SMT (Surveyor Micro Toolkit)
' Port and improvement of CHOStoNE / NEtoCHOS (original VBA).
'
' Local coordinate system:
'   Origin  : (N0, E0) in global grid (metres)
'   X-axis  : points along azimuth AziBEG (survey convention: 0=North, CW+)
'   Chainage: distance along X-axis  (metres, + forward)
'   Offset  : perpendicular distance (+right of travel / -left)
'
' Sign convention (offset):
'   + right of travel direction (clockwise from AziBEG)
'   - left  of travel direction
'
' AziBEG is always received in decimal degrees; converted to radians
' immediately on entry -- never passed in radians.
'
' Dependency: SMT_FPMath module (SMT_Pi, SMT_DegToRad, SMT_NormalizeAngle).
' ============================================================

' ============================================================
' Private: atan2(y, x) -- standard math convention
' Duplicated here because SMT_WCB version is Private (no cross-module access in VBA).
' Returns angle of vector (x, y) from +x axis, range (-pi, pi].
' ============================================================

Private Function SMT_Atan2(y As Double, x As Double) As Double
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

' ============================================================
' Private: shared forward computation (local -> global azimuth + distance)
' ============================================================

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

' ============================================================
' Public: Local -> Northing
' ============================================================

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

' ============================================================
' Public: Local -> Easting
' ============================================================

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

' ============================================================
' Public: Global -> Chainage
' ============================================================

Public Function SMT_GlobalToChn(n0 As Double, e0 As Double, aziBEG As Double, _
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
    SMT_GlobalToChn = dN * Cos(aziBEG_rad) + dE * Sin(aziBEG_rad)
End Function

' ============================================================
' Public: Global -> Offset
' ============================================================

Public Function SMT_GlobalToOfs(n0 As Double, e0 As Double, aziBEG As Double, _
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
    SMT_GlobalToOfs = -dN * Sin(aziBEG_rad) + dE * Cos(aziBEG_rad)
End Function

' ============================================================
' Expected values -- verified against Python
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
'   SMT_GlobalToChn(1000, 2000, 90, 1000, 2100) = 100.0
'     dN=0, dE=100 -> Chn = 0*cos(pi/2) + 100*sin(pi/2) = 100
'
'   SMT_GlobalToOfs(1000, 2000, 90,  950, 2000) =  50.0
'     dN=-50, dE=0 -> Ofs = -(-50)*sin(pi/2) + 0*cos(pi/2) = 50
' ============================================================
