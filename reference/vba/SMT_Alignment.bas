Attribute VB_Name = "SMT_Alignment"
Option Explicit

' ============================================================
' SMT_Alignment.bas  --  Horizontal alignment lookup + tangent azimuth
' Merged from: SMT_Align.bas (alignment.py port) + SMT_WCBatSta
'              (formerly Part 2 of SMT_Rotation3D.bas)
'
' Named Range SMT_Elements layout (8 columns per row, no header):
'   col1=StaStart  col2=StaEnd  col3=N       col4=E
'   col5=Azimuth(decimal degrees)  col6=Radius(signed metres)
'   col7=Type(T/C/SPIN/SPOUT)     col8=Transition(CLOTHOID/BLOSS/COSINE/SINE)
'
' Sign convention:
'   offset: +right of travel / -left.  radius: +right curve / -left curve.
'   k = 1/R (signed curvature).
'   Azimuth in col5 is decimal degrees; converted to radians immediately on read.
' Dependency: SMT_Core module must be imported in the same workbook.
' ============================================================

Private Const SMT_SPIRAL_STEPS As Long = 48  ' Simpson intervals (must be even)
Private Const SMT_STA_TOL As Double = 0.0001 ' station range tolerance (metres)
Private Const SMT_SINE_HALFWAVE_C As Double = 0.0226689447  ' Civil 3D closed-form tangent-length correction constant

' ============================================================
' Private: atan2(y, x)
' Duplicated here because SMT_Core version is Private.
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
        SMT_Atan2 = 0#  ' coincident: undefined; matches Python math.atan2(0,0)
    End If
End Function

' ============================================================
' Private: curvature shape integral F(tau) for spiral transitions
' F(tau) = integral_0^tau f(u) du
' f defines how curvature changes with normalised arc position tau = s/L.
' All shapes satisfy f(0)=0, f(1)=1, integral_0^1 f = 0.5.
' Unit: dimensionless (tau in [0,1]).
' ============================================================

Private Function SMT_ShapeIntegral(transition As String, tau As Double) As Double
    Dim PI As Double
    PI = SMT_Pi()
    Select Case UCase(Trim(transition))
        Case "BLOSS"
            SMT_ShapeIntegral = tau ^ 3# - tau ^ 4# / 2#
        Case "COSINE"
            SMT_ShapeIntegral = tau / 2# - Sin(PI * tau) / (2# * PI)
        Case "SINE"
            SMT_ShapeIntegral = tau ^ 2# / 2# - (1# - Cos(2# * PI * tau)) / (4# * PI ^ 2#)
        Case Else  ' CLOTHOID (default): f(tau)=tau -> F(tau)=tau^2/2
            SMT_ShapeIntegral = tau ^ 2# / 2#
    End Select
End Function

' ============================================================
' Private: accumulated turning angle at arc distance s from element start
' theta(s) = k_in*s + (k_out - k_in)*L*F(s/L)
' Unit: rad.  Sign: positive = right turn (azimuth increases clockwise).
' ============================================================

Private Function SMT_TurningAngle(kIn As Double, kOut As Double, L As Double, _
                                   transition As String, s As Double) As Double
    Dim tau As Double
    If L = 0# Then
        SMT_TurningAngle = kIn * s
    Else
        tau = s / L
        SMT_TurningAngle = kIn * s + (kOut - kIn) * L * SMT_ShapeIntegral(transition, tau)
    End If
End Function

' ============================================================
' Private: resolve signed curvatures k_in, k_out from Type + Radius
' SPIN : k_in=0 (tangent entry),  k_out=1/R (circular exit)
' SPOUT: k_in=1/R (circular entry), k_out=0 (tangent exit)
' C    : k_in=k_out=1/R
' T    : k_in=k_out=0
' Unit: radius in metres -> k in rad/m.
' ============================================================

Private Sub SMT_GetCurvatures(typStr As String, radius As Double, _
                               ByRef kIn As Double, ByRef kOut As Double)
    Dim k As Double
    If radius = 0# Then
        k = 0#
    Else
        k = 1# / radius
    End If
    Select Case UCase(Trim(typStr))
        Case "SPIN"
            kIn = 0#
            kOut = k
        Case "SPOUT"
            kIn = k
            kOut = 0#
        Case "C"
            kIn = k
            kOut = k
        Case Else  ' T or unknown: tangent
            kIn = 0#
            kOut = 0#
    End Select
End Sub

' ============================================================
' Private: COSINE (Civil 3D Sine Half-Wave) closed-form helpers
' Mirrors src/smt/alignment.py (_cosine_dydx, _cosine_arc_length,
' _cosine_solve_a, calculate_sine_halfwave_tangent_length,
' _sine_halfwave_point) after commit d8ebedd. No caching in this port --
' SMT_CosineSolveA bisects on [0,1] directly every call instead of using
' a cached bracket table (see plan doc design decision).
' ============================================================

Private Function SMT_CosineDydx(a As Double, bigX As Double, r As Double) As Double
    ' dy/dx at normalised parameter a -- same expression as the atan() argument
    ' in SMT_SineHalfwavePoint's theta (tan(theta) = dy/dx).
    Dim PI As Double
    PI = SMT_Pi()
    SMT_CosineDydx = bigX / r * (a / 2# - Sin(PI * a) / (2# * PI))
End Function

Private Function SMT_CosineArcLength(a As Double, bigX As Double, r As Double, _
                                      Optional nSeg As Long = SMT_SPIRAL_STEPS) As Double
    ' s(a) = integral[0..a] X*sqrt(1+(dy/dx)^2) da'  via Simpson quadrature.
    ' Same 48-interval Simpson pattern already used in SMT_PointOnElement (spiral branch).
    Dim h As Double, total As Double, ai As Double, integrand As Double
    Dim i As Long, w As Long
    h = a / CDbl(nSeg)
    total = 0#
    For i = 0 To nSeg
        ai = CDbl(i) * h
        integrand = bigX * Sqr(1# + SMT_CosineDydx(ai, bigX, r) ^ 2#)
        If i = 0 Or i = nSeg Then
            w = 1
        ElseIf (i Mod 2) = 1 Then
            w = 4
        Else
            w = 2
        End If
        total = total + CDbl(w) * integrand
    Next i
    SMT_CosineArcLength = total * h / 3#
End Function

Private Function SMT_CosineSolveA(d As Double, bigX As Double, r As Double, length As Double) As Double
    ' Solve s(a) = d for normalised parameter a: direct 50-iteration bisection on
    ' [0,1] -- no cached bracket table (design decision: see plan doc). Same
    ' 50-iteration bisection style already used in SMT_ProjectOnElement.
    Dim lo As Double, hi As Double, mid As Double, rAbs As Double
    Dim iter As Long
    rAbs = Abs(r)
    lo = 0#
    hi = 1#
    For iter = 1 To 50
        mid = (lo + hi) / 2#
        If SMT_CosineArcLength(mid, bigX, rAbs) < d Then
            lo = mid
        Else
            hi = mid
        End If
    Next iter
    SMT_CosineSolveA = (lo + hi) / 2#
End Function

Public Function SMT_CalcSineHalfwaveTangentLength(length As Double, r As Double) As Double
    ' Closed-form tangent-projected length X = L - 0.0226689447*L^3/R^2.
    ' Public (not Private) so it can also be called directly from a worksheet cell
    ' for the Excel verification checklist.
    SMT_CalcSineHalfwaveTangentLength = length - SMT_SINE_HALFWAVE_C * length ^ 3# / r ^ 2#
End Function

Private Function SMT_SineHalfwavePoint(d As Double, bigX As Double, r As Double, length As Double) As Variant
    ' COSINE transition shape, canonical (SPIN) form. Returns Variant array:
    ' (0)=x (true tangent-projected coord, a*X)  (1)=y (local offset)  (2)=theta (rad).
    ' d==length short-circuits to the exact a=1 closed form (same 1e-9 threshold as Python).
    Dim a As Double
    Dim res(2) As Double
    If Abs(d - length) < 0.000000001 Then
        a = 1#
    Else
        a = SMT_CosineSolveA(d, bigX, r, length)
    End If
    res(0) = a * bigX
    res(1) = bigX ^ 2# / r * (a ^ 2# / 4# - (1# - Cos(SMT_Pi() * a)) / (2# * SMT_Pi() ^ 2#))
    res(2) = Atn(SMT_CosineDydx(a, bigX, r))
    SMT_SineHalfwavePoint = res
End Function

' ============================================================
' Private: position and tangent azimuth at arc distance d from element start
' Returns Variant Array: (0)=N  (1)=E  (2)=tangentAzimuth(rad)
'
' Tangent (k_in=k_out=0): straight line.
' Circular (k_in=k_out=k): chord-and-half-angle formula.
' Spiral (k_in<>k_out): Simpson integration of (cos theta, sin theta),
'   48 intervals -- matches Python oracle exactly for CLOTHOID/BLOSS/SINE.
'   COSINE (pure SPIN/SPOUT) now bypasses this generic path -- see the
'   dedicated closed-form branch above.
' ============================================================

Private Function SMT_PointOnElement(n0 As Double, e0 As Double, az0 As Double, _
                                     kIn As Double, kOut As Double, L As Double, _
                                     transition As String, d As Double) As Variant
    Dim res(2) As Double
    Dim k As Double, theta As Double, chord As Double, chordAz As Double
    Dim nSeg As Long, i As Long, w As Long
    Dim h As Double, sumX As Double, sumY As Double
    Dim s As Double, th As Double
    Dim ca As Double, sa As Double, x As Double, y As Double
    Dim lenEl As Double, rr As Double, bigX As Double
    Dim ptSine As Variant
    Dim xLocal As Double, yLocal As Double, thLocal As Double
    Dim xEnd As Double, yEnd As Double, thTotal As Double
    Dim xG As Double, yG As Double, thG As Double
    Dim dxs As Double, dys As Double

    If kIn = 0# And kOut = 0# Then
        ' Tangent: straight line along entry azimuth
        res(0) = n0 + d * Cos(az0)
        res(1) = e0 + d * Sin(az0)
        res(2) = az0

    ElseIf kIn = kOut Then
        ' Circular: constant curvature; chord bisects the arc angle
        k = kIn
        theta = k * d
        chord = (2# / Abs(k)) * Abs(Sin(theta / 2#))
        chordAz = az0 + theta / 2#
        res(0) = n0 + chord * Cos(chordAz)
        res(1) = e0 + chord * Sin(chordAz)
        res(2) = SMT_NormalizeAngle(az0 + theta)

    ElseIf UCase(Trim(transition)) = "COSINE" And ((kIn = 0#) <> (kOut = 0#)) Then
        ' COSINE (Civil 3D Sine Half-Wave) pure SPIN/SPOUT closed form -- mirrors
        ' alignment.py calculate_point_on_element:378-401. Bypasses the generic
        ' Simpson-over-theta path below entirely for this case.
        lenEl = L
        If kIn = 0# Then
            ' SPIN: curvature 0 -> 1/R, canonical form used directly
            rr = 1# / kOut
            bigX = SMT_CalcSineHalfwaveTangentLength(lenEl, rr)
            ptSine = SMT_SineHalfwavePoint(d, bigX, rr, lenEl)
            xLocal = ptSine(0): yLocal = ptSine(1): thLocal = ptSine(2)
        Else
            ' SPOUT: curvature 1/R -> 0, mirror canonical form via s <-> L-d
            rr = 1# / kIn
            bigX = SMT_CalcSineHalfwaveTangentLength(lenEl, rr)
            ptSine = SMT_SineHalfwavePoint(lenEl, bigX, rr, lenEl)
            xEnd = ptSine(0): yEnd = ptSine(1): thTotal = ptSine(2)
            ptSine = SMT_SineHalfwavePoint(lenEl - d, bigX, rr, lenEl)
            xG = ptSine(0): yG = ptSine(1): thG = ptSine(2)
            dxs = xEnd - xG
            dys = yEnd - yG
            xLocal = dxs * Cos(thTotal) + dys * Sin(thTotal)
            yLocal = dxs * Sin(thTotal) - dys * Cos(thTotal)
            thLocal = thTotal - thG
        End If
        ca = Cos(az0)
        sa = Sin(az0)
        res(0) = n0 + xLocal * ca - yLocal * sa
        res(1) = e0 + xLocal * sa + yLocal * ca
        res(2) = SMT_NormalizeAngle(az0 + thLocal)

    Else
        ' Spiral: Simpson integration in local frame (x=along entry tangent, y=left)
        nSeg = SMT_SPIRAL_STEPS
        h = d / CDbl(nSeg)
        sumX = 0#
        sumY = 0#
        For i = 0 To nSeg
            s = CDbl(i) * h
            th = SMT_TurningAngle(kIn, kOut, L, transition, s)
            If i = 0 Or i = nSeg Then
                w = 1
            ElseIf (i Mod 2) = 1 Then
                w = 4
            Else
                w = 2
            End If
            sumX = sumX + CDbl(w) * Cos(th)
            sumY = sumY + CDbl(w) * Sin(th)
        Next i
        x = sumX * h / 3#
        y = sumY * h / 3#
        ca = Cos(az0)
        sa = Sin(az0)
        res(0) = n0 + x * ca - y * sa
        res(1) = e0 + x * sa + y * ca
        res(2) = SMT_NormalizeAngle(az0 + SMT_TurningAngle(kIn, kOut, L, transition, d))
    End If

    SMT_PointOnElement = res
End Function

' ============================================================
' Private: project external point (pN, pE) onto one element
' Returns Variant Array: (0)=sta  (1)=offset  (2)=d  (3)=inRange(1/0)
' offset: +right of travel / -left.
'
' Tangent  : dot-product foot.
' Circular : angle swept from centre of curvature.
' Spiral   : bisection on g(s) = (P - Q(s)) . tangentDir(s) = 0 (50 iterations).
' ============================================================

Private Function SMT_ProjectOnElement(staStart As Double, staEnd As Double, _
                                       n0 As Double, e0 As Double, az0 As Double, _
                                       kIn As Double, kOut As Double, L As Double, _
                                       transition As String, _
                                       pN As Double, pE As Double) As Variant
    Dim res(3) As Double
    Dim dN As Double, dE As Double, ca As Double, sa As Double
    Dim d As Double, off As Double
    Dim k As Double, R As Double
    Dim centerN As Double, centerE As Double, rho As Double
    Dim phi0 As Double, phiP As Double, dArc As Double
    Dim g0 As Double, gL As Double, gMid As Double, gLo As Double
    Dim lo As Double, hi As Double, mid As Double
    Dim iter As Long
    Dim pt As Variant
    Dim sN As Double, sE As Double, sAz As Double, sStar As Double
    Dim inRange As Boolean

    If kIn = 0# And kOut = 0# Then
        ' Tangent: foot via dot-product projection onto the infinite line
        dN = pN - n0
        dE = pE - e0
        ca = Cos(az0)
        sa = Sin(az0)
        d = dN * ca + dE * sa
        off = -dN * sa + dE * ca
        res(0) = staStart + d
        res(1) = off
        res(2) = d
        If d >= -SMT_STA_TOL And d <= L + SMT_STA_TOL Then
            res(3) = 1#
        Else
            res(3) = 0#
        End If

    ElseIf kIn = kOut Then
        ' Circular: angle swept from centre of curvature
        ' centre = (n - R*sin(az), e + R*cos(az))  -- perpendicular right for k>0
        k = kIn
        R = 1# / k
        centerN = n0 - R * Sin(az0)
        centerE = e0 + R * Cos(az0)
        rho = Sqr((pN - centerN) ^ 2# + (pE - centerE) ^ 2#)
        phi0 = SMT_Atan2(e0 - centerE, n0 - centerN)
        phiP = SMT_Atan2(pE - centerE, pN - centerN)
        dArc = SMT_AngleDiff(phiP, phi0) / k
        If k > 0# Then
            off = Abs(R) - rho   ' +inside arc (right side) for right curve
        Else
            off = -(Abs(R) - rho)
        End If
        res(0) = staStart + dArc
        res(1) = off
        res(2) = dArc
        If dArc >= -SMT_STA_TOL And dArc <= L + SMT_STA_TOL Then
            res(3) = 1#
        Else
            res(3) = 0#
        End If

    Else
        ' Spiral: bisection on g(s) = (P - Q(s)) . tangentDir(s) = 0
        pt = SMT_PointOnElement(n0, e0, az0, kIn, kOut, L, transition, 0#)
        g0 = (pN - pt(0)) * Cos(pt(2)) + (pE - pt(1)) * Sin(pt(2))
        pt = SMT_PointOnElement(n0, e0, az0, kIn, kOut, L, transition, L)
        gL = (pN - pt(0)) * Cos(pt(2)) + (pE - pt(1)) * Sin(pt(2))

        inRange = (g0 = 0#) Or (gL = 0#) Or ((g0 > 0#) <> (gL > 0#))

        If inRange Then
            lo = 0#
            hi = L
            gLo = g0
            For iter = 1 To 50
                mid = (lo + hi) / 2#
                pt = SMT_PointOnElement(n0, e0, az0, kIn, kOut, L, transition, mid)
                gMid = (pN - pt(0)) * Cos(pt(2)) + (pE - pt(1)) * Sin(pt(2))
                If (gLo > 0#) = (gMid > 0#) Then
                    lo = mid
                    gLo = gMid
                Else
                    hi = mid
                End If
            Next iter
            sStar = (lo + hi) / 2#
        Else
            If Abs(g0) < Abs(gL) Then
                sStar = 0#
            Else
                sStar = L
            End If
        End If

        pt = SMT_PointOnElement(n0, e0, az0, kIn, kOut, L, transition, sStar)
        sN = pt(0)
        sE = pt(1)
        sAz = pt(2)
        off = -(pN - sN) * Sin(sAz) + (pE - sE) * Cos(sAz)

        res(0) = staStart + sStar
        res(1) = off
        res(2) = sStar
        If inRange Then
            res(3) = 1#
        Else
            res(3) = 0#
        End If
    End If

    SMT_ProjectOnElement = res
End Function

' ============================================================
' Private: forward solve -- sta + offset -> (N, E) across all elements
' Returns Variant Array (0)=N  (1)=E, or CVErr(xlErrValue) if sta out of range.
' ============================================================

Private Function SMT_SolveForward(sta As Double, offset As Double, _
                                   rng As Range) As Variant
    Dim nRows As Long, i As Long
    Dim staStart As Double, staEnd As Double
    Dim n0 As Double, e0 As Double
    Dim azDeg As Double, az0 As Double
    Dim radius As Double, typStr As String, transStr As String
    Dim kIn As Double, kOut As Double, L As Double, d As Double
    Dim pt As Variant, offAz As Double
    Dim res(1) As Double

    nRows = rng.Rows.Count
    For i = 1 To nRows
        staStart = CDbl(rng.Cells(i, 1).Value)
        staEnd = CDbl(rng.Cells(i, 2).Value)
        If sta >= staStart - SMT_STA_TOL And sta <= staEnd + SMT_STA_TOL Then
            n0 = CDbl(rng.Cells(i, 3).Value)
            e0 = CDbl(rng.Cells(i, 4).Value)
            azDeg = CDbl(rng.Cells(i, 5).Value)
            az0 = SMT_DegToRad(azDeg)  ' degrees -> radians immediately on read
            radius = CDbl(rng.Cells(i, 6).Value)
            typStr = CStr(rng.Cells(i, 7).Value)
            transStr = CStr(rng.Cells(i, 8).Value)
            If Len(Trim(transStr)) = 0 Then transStr = "CLOTHOID"
            kIn = 0#
            kOut = 0#
            SMT_GetCurvatures typStr, radius, kIn, kOut
            L = staEnd - staStart
            d = sta - staStart
            If d < 0# Then d = 0#  ' clamp tolerance overshoot at element start
            pt = SMT_PointOnElement(n0, e0, az0, kIn, kOut, L, transStr, d)
            If offset <> 0# Then
                offAz = SMT_NormalizeAngle(pt(2) + SMT_Pi() / 2#)
                res(0) = pt(0) + offset * Cos(offAz)
                res(1) = pt(1) + offset * Sin(offAz)
            Else
                res(0) = pt(0)
                res(1) = pt(1)
            End If
            SMT_SolveForward = res
            Exit Function
        End If
    Next i
    SMT_SolveForward = CVErr(xlErrValue)
End Function

' ============================================================
' Private: inverse solve -- (N, E) -> (sta, offset) across all elements
' Iterates every element; keeps in-range projection with minimum |offset|.
' Returns Variant Array (0)=sta  (1)=offset, or CVErr(xlErrValue) if no projection.
' ============================================================

Private Function SMT_SolveInverse(pN As Double, pE As Double, _
                                   rng As Range) As Variant
    Dim nRows As Long, i As Long
    Dim staStart As Double, staEnd As Double
    Dim n0 As Double, e0 As Double
    Dim azDeg As Double, az0 As Double
    Dim radius As Double, typStr As String, transStr As String
    Dim kIn As Double, kOut As Double, L As Double
    Dim pr As Variant
    Dim bestSta As Double, bestOff As Double, hasBest As Boolean
    Dim res(1) As Double

    hasBest = False
    nRows = rng.Rows.Count
    For i = 1 To nRows
        staStart = CDbl(rng.Cells(i, 1).Value)
        staEnd = CDbl(rng.Cells(i, 2).Value)
        n0 = CDbl(rng.Cells(i, 3).Value)
        e0 = CDbl(rng.Cells(i, 4).Value)
        azDeg = CDbl(rng.Cells(i, 5).Value)
        az0 = SMT_DegToRad(azDeg)  ' degrees -> radians immediately on read
        radius = CDbl(rng.Cells(i, 6).Value)
        typStr = CStr(rng.Cells(i, 7).Value)
        transStr = CStr(rng.Cells(i, 8).Value)
        If Len(Trim(transStr)) = 0 Then transStr = "CLOTHOID"
        kIn = 0#
        kOut = 0#
        SMT_GetCurvatures typStr, radius, kIn, kOut
        L = staEnd - staStart
        pr = SMT_ProjectOnElement(staStart, staEnd, n0, e0, az0, _
                                   kIn, kOut, L, transStr, pN, pE)
        If pr(3) = 1# Then
            If Not hasBest Or Abs(pr(1)) < Abs(bestOff) Then
                bestSta = pr(0)
                bestOff = pr(1)
                hasBest = True
            End If
        End If
    Next i

    If hasBest Then
        res(0) = bestSta
        res(1) = bestOff
        SMT_SolveInverse = res
    Else
        SMT_SolveInverse = CVErr(xlErrValue)
    End If
End Function

' ============================================================
' Public: Forward -- station + offset -> Northing
' ============================================================

Public Function SMT_StaToN(sta As Double, offset As Double, rng As Range) As Variant
    ' Forward: station + perpendicular offset -> Northing (metres).
    ' sta   : arc distance along alignment centre line (metres).
    ' offset: +right of travel / -left (metres); 0 for centre line.
    ' rng   : SMT_Elements Named Range -- 8 columns, no header row.
    '         col5 Azimuth must be decimal degrees; converted to rad internally.
    ' Returns #VALUE! when sta is outside the alignment.
    Dim pt As Variant
    pt = SMT_SolveForward(sta, offset, rng)
    If IsError(pt) Then
        SMT_StaToN = pt
    Else
        SMT_StaToN = pt(0)
    End If
End Function

' ============================================================
' Public: Forward -- station + offset -> Easting
' ============================================================

Public Function SMT_StaToE(sta As Double, offset As Double, rng As Range) As Variant
    ' Forward: station + perpendicular offset -> Easting (metres).
    ' sta   : arc distance along alignment centre line (metres).
    ' offset: +right of travel / -left (metres); 0 for centre line.
    ' rng   : SMT_Elements Named Range -- 8 columns, no header row.
    '         col5 Azimuth must be decimal degrees; converted to rad internally.
    ' Returns #VALUE! when sta is outside the alignment.
    Dim pt As Variant
    pt = SMT_SolveForward(sta, offset, rng)
    If IsError(pt) Then
        SMT_StaToE = pt
    Else
        SMT_StaToE = pt(1)
    End If
End Function

' ============================================================
' Public: Inverse -- N, E -> Station
' ============================================================

Public Function SMT_CoordToSta(n As Double, e As Double, rng As Range) As Variant
    ' Inverse: grid coordinate -> closest alignment station (metres).
    ' n, e  : Northing and Easting (metres).
    ' rng   : SMT_Elements Named Range -- 8 columns, no header row.
    '         col5 Azimuth must be decimal degrees; converted to rad internally.
    ' Projects onto every element; returns station where |offset| is minimum.
    ' Returns #VALUE! when the point projects outside all elements.
    Dim pr As Variant
    pr = SMT_SolveInverse(n, e, rng)
    If IsError(pr) Then
        SMT_CoordToSta = pr
    Else
        SMT_CoordToSta = pr(0)
    End If
End Function

' ============================================================
' Public: Inverse -- N, E -> Offset
' ============================================================

Public Function SMT_CoordToOffset(n As Double, e As Double, rng As Range) As Variant
    ' Inverse: grid coordinate -> signed perpendicular offset from centre line (metres).
    ' n, e  : Northing and Easting (metres).
    ' rng   : SMT_Elements Named Range -- 8 columns, no header row.
    '         col5 Azimuth must be decimal degrees; converted to rad internally.
    ' offset: +right of travel / -left.
    ' Returns #VALUE! when the point projects outside all elements.
    Dim pr As Variant
    pr = SMT_SolveInverse(n, e, rng)
    If IsError(pr) Then
        SMT_CoordToOffset = pr
    Else
        SMT_CoordToOffset = pr(1)
    End If
End Function

' ============================================================
' Public: WCB (azimuth, decimal degrees) at a given station
' ============================================================

Public Function SMT_WCBatSta(sta As Double, rng As Range) As Variant
    ' WCB (whole-circle bearing / azimuth) of the alignment centre-line tangent
    ' at station sta, in decimal degrees, normalised to [0, 360).
    '
    ' sta : arc distance along alignment (metres).
    ' rng : SMT_Elements Named Range -- 8 columns, no header:
    '         col1=StaStart  col2=StaEnd  col3=N  col4=E
    '         col5=Azimuth(decimal deg)   col6=Radius(signed m)
    '         col7=Type(T/C/SPIN/SPOUT)   col8=Transition
    '
    ' Type formulas (d = sta - StaStart, L = StaEnd - StaStart):
    '   T    : WCB = Azimuth  (constant tangent)
    '   C    : theta = d / R                       [rad]; R = signed radius
    '   SPIN : theta = d^2 / (2*R*L)               [rad]; clothoid k(s)=s/(R*L)
    '   SPOUT: theta = d/R - d^2 / (2*R*L)         [rad]; clothoid k_in=1/R -> k_out=0
    '   WCB  = Azimuth_deg + SMT_RadToDeg(theta), then normalised to [0, 360).
    '
    ' Sign: R>0 = right curve = azimuth increases; R<0 = left = azimuth decreases.
    ' Returns #VALUE! when sta is outside all elements.
    Dim nRows As Long, i As Long
    Dim staStart As Double, staEnd As Double
    Dim azDeg As Double, radius As Double
    Dim typStr As String
    Dim isLast As Boolean
    Dim d As Double, L As Double
    Dim theta_rad As Double, wcb_raw As Double

    nRows = rng.Rows.Count
    For i = 1 To nRows
        staStart = CDbl(rng.Cells(i, 1).Value)
        staEnd   = CDbl(rng.Cells(i, 2).Value)
        isLast   = (i = nRows)
        If sta >= staStart And (sta < staEnd Or (isLast And sta <= staEnd)) Then
            azDeg  = CDbl(rng.Cells(i, 5).Value)   ' entry azimuth at StaStart (degrees)
            radius = CDbl(rng.Cells(i, 6).Value)   ' signed radius (m); 0 = tangent
            typStr = CStr(rng.Cells(i, 7).Value)
            d = sta - staStart
            L = staEnd - staStart

            Select Case UCase(Trim(typStr))
                Case "T"
                    theta_rad = 0#   ' tangent: azimuth is constant

                Case "C"
                    ' Circular arc: uniform curvature k = 1/R
                    ' theta = d / R  (radians; sign follows R: +right, -left)
                    If radius <> 0# Then
                        theta_rad = d / radius
                    Else
                        theta_rad = 0#
                    End If

                Case "SPIN"
                    ' Clothoid spiral-in (tangent -> curve):
                    ' k(s) = s / (R*L),  theta = integral_0^d k ds = d^2 / (2*R*L)
                    If radius <> 0# And L <> 0# Then
                        theta_rad = (d * d) / (2# * radius * L)
                    Else
                        theta_rad = 0#
                    End If

                Case "SPOUT"
                    ' Clothoid spiral-out (curve -> tangent):
                    ' k(s) = 1/R - s/(R*L),  theta = d/R - d^2 / (2*R*L)
                    If radius <> 0# And L <> 0# Then
                        theta_rad = d / radius - (d * d) / (2# * radius * L)
                    Else
                        theta_rad = 0#
                    End If

                Case Else
                    theta_rad = 0#   ' unknown type: treat as tangent
            End Select

            wcb_raw = azDeg + SMT_RadToDeg(theta_rad)
            ' Normalise to [0, 360) via radians round-trip
            SMT_WCBatSta = SMT_RadToDeg(SMT_NormalizeAngle(SMT_DegToRad(wcb_raw)))
            Exit Function
        End If
    Next i

    SMT_WCBatSta = CVErr(xlErrValue)   ' sta outside all elements
End Function

' ============================================================
' Expected values -- verified against Python (src/smt/alignment.py)
' using the project dataset loaded into the SMT_Elements Named Range:
'
'   SMT_StaToN(0, 0, SMT_Elements)                  = 1568000.0
'   SMT_StaToE(519.615, 0, SMT_Elements)             = 678519.615
'   SMT_CoordToSta(1568000, 678000, SMT_Elements)    = 0.0
'   SMT_CoordToOffset(1568000, 678000, SMT_Elements) = 0.0
'
'   SMT_WCBatSta(0, SMT_Elements) = 90.0
'     First element: Type=T, Azimuth=90 deg -> WCB = 90.0
'   For C element with R=300, az=90, sta=StaStart+157.08 (quarter circle):
'     theta = 157.08/300 = 0.5236 rad = 30.0 deg -> WCB = 120.0 deg
' ============================================================
