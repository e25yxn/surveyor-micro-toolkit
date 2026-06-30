Attribute VB_Name = "SMT_Crossfall"
Option Explicit

' ============================================================
' SMT_Crossfall.bas  --  VBA port of src/smt/crossfall.py
' SMT (Surveyor Micro Toolkit) -- Crossfall / superelevation lookup
'
' Named Range SMT_Crossfall layout (6 columns per row, no header):
'   col1=StaStart   col2=StaEnd
'   col3=CF_L_Start (left crossfall at StaStart, %)
'   col4=CF_L_End   (left crossfall at StaEnd,   %)
'   col5=CF_R_Start (right crossfall at StaStart, %)
'   col6=CF_R_End   (right crossfall at StaEnd,   %)
'
' Sign convention (both left and right):
'   Negative (-) : falls away from centre line -- normal drainage (e.g. -2 %)
'   Positive (+) : falls toward centre line   -- superelevation (e.g. +7 %)
'
' Interpolation: linear within each segment (equivalent to Python type 'V').
'   CF(sta) = CF_Start + (CF_End - CF_Start) * (sta - StaStart) / (StaEnd - StaStart)
'   When CF_Start = CF_End the value is constant (no division performed).
'
' Station range rule (matches Python oracle):
'   Interior segments: sta in [StaStart, StaEnd)  -- exclusive at end
'   Last segment     : sta in [StaStart, StaEnd]  -- inclusive at end
'
' Standalone module (no dependency on other SMT modules).
' ============================================================

' ============================================================
' Private: linear interpolation within one segment
' ============================================================

Private Function SMT_CfInterp(sta As Double, staStart As Double, staEnd As Double, _
                               cfStart As Double, cfEnd As Double) As Double
    ' Linear crossfall interpolation.
    ' CF(sta) = cfStart + (cfEnd - cfStart) * (sta - staStart) / (staEnd - staStart)
    ' Returns cfStart immediately when segment has zero length or constant crossfall.
    ' Unit: crossfall in %; sta values in metres.
    Dim L As Double
    L = staEnd - staStart
    If L = 0# Or cfStart = cfEnd Then
        SMT_CfInterp = cfStart
    Else
        SMT_CfInterp = cfStart + (cfEnd - cfStart) * (sta - staStart) / L
    End If
End Function

' ============================================================
' Private: crossfall lookup -- shared logic for left and right
' ============================================================

Private Function SMT_CfLookup(sta As Double, rng As Range, _
                               colStart As Long, colEnd As Long) As Variant
    ' Search rng for the segment containing sta and interpolate crossfall.
    ' colStart, colEnd: 1-based column indices for CF_Start and CF_End values.
    ' Returns #VALUE! when sta is outside all segments.
    Dim nRows As Long, i As Long
    Dim staStart As Double, staEnd As Double
    Dim cfStart As Double, cfEnd As Double
    Dim isLast As Boolean

    nRows = rng.Rows.Count
    For i = 1 To nRows
        staStart = CDbl(rng.Cells(i, 1).Value)
        staEnd   = CDbl(rng.Cells(i, 2).Value)
        isLast   = (i = nRows)
        If sta >= staStart And (sta < staEnd Or (isLast And sta <= staEnd)) Then
            cfStart = CDbl(rng.Cells(i, colStart).Value)
            cfEnd   = CDbl(rng.Cells(i, colEnd).Value)
            SMT_CfLookup = SMT_CfInterp(sta, staStart, staEnd, cfStart, cfEnd)
            Exit Function
        End If
    Next i

    SMT_CfLookup = CVErr(xlErrValue)   ' sta outside all segments
End Function

' ============================================================
' Public: Left crossfall at station
' ============================================================

Public Function SMT_CrossfallLeft(sta As Double, rng As Range) As Variant
    ' Left crossfall (%) at station sta.
    ' sta : arc distance along alignment (metres).
    ' rng : SMT_Crossfall Named Range -- 6 columns, no header row.
    '
    ' Uses col3 (CF_L_Start) and col4 (CF_L_End) for linear interpolation.
    ' Sign: - = falls away from centre line (normal); + = toward centre (superelevation).
    ' Returns #VALUE! when sta is outside the crossfall table range.
    SMT_CrossfallLeft = SMT_CfLookup(sta, rng, 3, 4)
End Function

' ============================================================
' Public: Right crossfall at station
' ============================================================

Public Function SMT_CrossfallRight(sta As Double, rng As Range) As Variant
    ' Right crossfall (%) at station sta.
    ' sta : arc distance along alignment (metres).
    ' rng : SMT_Crossfall Named Range -- 6 columns, no header row.
    '
    ' Uses col5 (CF_R_Start) and col6 (CF_R_End) for linear interpolation.
    ' Sign: - = falls away from centre line (normal); + = toward centre (superelevation).
    ' Returns #VALUE! when sta is outside the crossfall table range.
    SMT_CrossfallRight = SMT_CfLookup(sta, rng, 5, 6)
End Function

' ============================================================
' Expected values -- verified against Python (src/smt/crossfall.py)
' using the project dataset loaded into the SMT_Crossfall Named Range.
'
' Example segment layout illustrating the three zone types:
'   [1]  sta=0-500     CF_L_Start=-2, CF_L_End=-2  CF_R_Start=-2, CF_R_End=-2  (normal)
'   [2]  sta=500-560   CF_L_Start=-2, CF_L_End=0   CF_R_Start=-2, CF_R_End=-2  (runout, left ramps up)
'   [3]  sta=560-...   CF_L_Start=0,  CF_L_End=7   CF_R_Start=-2, CF_R_End=-2  (transition to full super)
'
'   SMT_CrossfallLeft(0,   SMT_Crossfall) = -2.0   (normal section, constant)
'   SMT_CrossfallLeft(530, SMT_Crossfall) = -1.0   (runout midpoint: -2+(-2->0)*30/60)
'   SMT_CrossfallLeft(700, SMT_Crossfall) =  7.0   (full superelevation)
'   SMT_CrossfallRight(530, SMT_Crossfall) = -2.0  (right side unchanged during left runout)
' ============================================================
