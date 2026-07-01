"""landxml - LandXML 1.2 export for horizontal alignments.

Pure function; no I/O.  Produces a well-formed LandXML 1.2 XML string
that Civil 3D 2023 can import directly.

Coordinates: "N E" format (northing first), 6 decimal places.
Azimuths: decimal degrees.  Units: metric, linearUnit=meter.
Sign convention: k>0 → rot="cw" (right turn); k<0 → rot="ccw" (left turn).
dirStart/dirEnd = entry/exit azimuth converted to Civil 3D direction
convention (decimal degrees, 0=East counterclockwise) via _to_civil_dir,
on every Curve and Spiral.
"""
from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from datetime import datetime

from . import fpmath
from .alignment import Element, calculate_exit_state
from .builders.alignment_builder import BuildResult

_NS = 'http://www.landxml.org/schema/LandXML-1.2'

ET.register_namespace('', _NS)

_SPIRAL_TYPE = {
    'CLOTHOID': 'clothoid',
    'BLOSS': 'bloss',
    'SINE': 'sineHalfWave',
    'COSINE': 'sinusoid',
}


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _end_ne(i: int, elements: list[Element]) -> tuple[float, float]:
    if i < len(elements) - 1:
        return elements[i + 1].n, elements[i + 1].e
    state = calculate_exit_state(elements[-1])
    return state.n, state.e


def _exit_azimuth(i: int, elements: list[Element]) -> float:
    if i < len(elements) - 1:
        return elements[i + 1].azimuth
    return calculate_exit_state(elements[-1]).azimuth


def _to_civil_dir(az_rad: float) -> float:
    """Convert SMT survey azimuth (rad, 0=North clockwise) to Civil 3D
    direction convention (decimal degrees, 0=East counterclockwise)."""
    return (450.0 - fpmath.rad_to_deg(az_rad)) % 360.0


def _curve_center(n: float, e: float, azimuth_rad: float, k: float) -> tuple[float, float]:
    R = 1.0 / k   # signed: k>0 → right, k<0 → left
    return n - R * math.sin(azimuth_rad), e + R * math.cos(azimuth_rad)


def _rotation(k: float) -> str:
    return 'cw' if k > 0 else 'ccw'


def _spiral_lx_type(transition: str) -> str:
    return _SPIRAL_TYPE.get(transition.upper(), 'clothoid')


def _coord(n: float, e: float) -> str:
    return f'{n:.6f} {e:.6f}'


def _sub(parent: ET.Element, tag: str, text: str | None = None, **attrs: str) -> ET.Element:
    el = ET.SubElement(parent, f'{{{_NS}}}{tag}', **attrs)
    if text is not None:
        el.text = text
    return el


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def export_alignment_landxml(build_result: BuildResult, name: str = 'alignment') -> str:
    """Convert BuildResult to LandXML 1.2 XML string (Civil 3D 2023 compatible).

    Units: metric/meter.  Coordinates: "N E" (northing first), 6 dp.
    rot="cw" for k>0 (right turn), rot="ccw" for k<0 (left turn).
    Curve: <Center> child tag; dirStart/dirEnd (entry/exit azimuth, Civil 3D
    direction convention, decimal degrees).
    Spiral: dirStart/dirEnd (entry/exit azimuth, Civil 3D direction convention).
    radiusStart/radiusEnd="INF" for the infinite-radius end of spiral elements.
    """
    elements = build_result.elements
    if not elements:
        raise ValueError('BuildResult has no elements')

    total_length = elements[-1].sta_end - elements[0].sta_start
    now = datetime.now()

    root = ET.Element(
        f'{{{_NS}}}LandXML',
        version='1.2',
        date=now.strftime('%Y-%m-%d'),
        time=now.strftime('%H:%M:%S'),
    )

    units = ET.SubElement(root, f'{{{_NS}}}Units')
    ET.SubElement(units, f'{{{_NS}}}Metric',
                  linearUnit='meter',
                  areaUnit='squareMeter',
                  volumeUnit='cubicMeter',
                  angularUnit='decimal dd',
                  directionUnit='decimal dd')

    alignments = ET.SubElement(root, f'{{{_NS}}}Alignments')
    align = ET.SubElement(alignments, f'{{{_NS}}}Alignment',
                          name=name,
                          length=f'{total_length:.6f}',
                          staStart=f'{elements[0].sta_start:.6f}')
    coord_geom = ET.SubElement(align, f'{{{_NS}}}CoordGeom')

    for i, el in enumerate(elements):
        end_n, end_e = _end_ne(i, elements)
        length = el.sta_end - el.sta_start

        if el.type == 'T':
            tag = ET.SubElement(coord_geom, f'{{{_NS}}}Line',
                                length=f'{length:.6f}')
            _sub(tag, 'Start', _coord(el.n, el.e))
            _sub(tag, 'End',   _coord(end_n, end_e))

        elif el.type == 'C':
            k = el.k_in
            R = abs(1.0 / k)
            cn, ce = _curve_center(el.n, el.e, el.azimuth, k)
            exit_az = _exit_azimuth(i, elements)
            tag = ET.SubElement(coord_geom, f'{{{_NS}}}Curve',
                                rot=_rotation(k),
                                radius=f'{R:.6f}',
                                length=f'{length:.6f}',
                                dirStart=f'{_to_civil_dir(el.azimuth):.6f}',
                                dirEnd=f'{_to_civil_dir(exit_az):.6f}')
            _sub(tag, 'Start',  _coord(el.n, el.e))
            _sub(tag, 'Center', _coord(cn, ce))
            _sub(tag, 'End',    _coord(end_n, end_e))

        elif el.type == 'SPIN':
            k_out = el.k_out
            R_out = abs(1.0 / k_out)
            exit_az = _exit_azimuth(i, elements)
            tag = ET.SubElement(coord_geom, f'{{{_NS}}}Spiral',
                                type=_spiral_lx_type(el.transition),
                                rot=_rotation(k_out),
                                radiusStart='INF',
                                radiusEnd=f'{R_out:.6f}',
                                spiType='toCurve',
                                length=f'{length:.6f}',
                                dirStart=f'{_to_civil_dir(el.azimuth):.6f}',
                                dirEnd=f'{_to_civil_dir(exit_az):.6f}')
            _sub(tag, 'Start', _coord(el.n, el.e))
            _sub(tag, 'End',   _coord(end_n, end_e))

        elif el.type == 'SPOUT':
            k_in = el.k_in
            R_in = abs(1.0 / k_in)
            exit_az = _exit_azimuth(i, elements)
            tag = ET.SubElement(coord_geom, f'{{{_NS}}}Spiral',
                                type=_spiral_lx_type(el.transition),
                                rot=_rotation(k_in),
                                radiusStart=f'{R_in:.6f}',
                                radiusEnd='INF',
                                spiType='fromCurve',
                                length=f'{length:.6f}',
                                dirStart=f'{_to_civil_dir(el.azimuth):.6f}',
                                dirEnd=f'{_to_civil_dir(exit_az):.6f}')
            _sub(tag, 'Start', _coord(el.n, el.e))
            _sub(tag, 'End',   _coord(end_n, end_e))

    ET.indent(root, space='  ')
    xml_body = ET.tostring(root, encoding='unicode')
    return '<?xml version="1.0" encoding="utf-8"?>\n' + xml_body
