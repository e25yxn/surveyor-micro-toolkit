"""Tests for smt.webhelpers — pure CSV-parsing helpers used by app.py.

These import smt.webhelpers directly (not app.py), so the tests are green
whether or not streamlit is installed. Uses small in-memory CSV byte strings
to stand in for Streamlit's UploadedFile content (UploadedFile.getvalue()
returns bytes).
"""
from smt.webhelpers import (
    parse_drawing_points,
    parse_element_rows,
    parse_field_points,
    read_csv_rows,
)


def test_read_csv_rows_round_trips():
    rows = read_csv_rows(b'a,b\r\n1,2\r\n')
    assert rows == [['a', 'b'], ['1', '2']]


def test_parse_field_points_with_disc():
    rows = read_csv_rows(b'NAME,N,E,Z,DISC\r\nP1,1000,2000,10,0.005\r\n')
    points = parse_field_points(rows)
    assert points == [{'name': 'P1', 'n': 1000.0, 'e': 2000.0, 'z': 10.0, 'disc': '0.005'}]


def test_parse_field_points_missing_disc_defaults_to_empty_string():
    rows = read_csv_rows(b'NAME,N,E,Z\r\nP1,1000,2000,10\r\n')
    points = parse_field_points(rows)
    assert points[0]['disc'] == ''
    assert points[0]['disc'] != 0.0


def test_parse_field_points_tolerates_blank_lines():
    rows = read_csv_rows(b'NAME,N,E,Z,DISC\r\nP1,1000,2000,10,\r\n\r\nP2,1001,2001,11,\r\n')
    points = parse_field_points(rows)
    assert [p['name'] for p in points] == ['P1', 'P2']


def test_parse_drawing_points_standard_rows():
    rows = read_csv_rows(b'Name,STA,N,E\r\nPI1,0,1000,2000\r\nPT1,100,1050,2050\r\n')
    points = parse_drawing_points(rows)
    assert points == [
        {'name': 'PI1', 'sta': 0.0, 'n': 1000.0, 'e': 2000.0},
        {'name': 'PT1', 'sta': 100.0, 'n': 1050.0, 'e': 2050.0},
    ]


def test_parse_drawing_points_tolerates_blank_lines():
    rows = read_csv_rows(b'Name,STA,N,E\r\nPI1,0,1000,2000\r\n\r\nPT1,100,1050,2050\r\n')
    points = parse_drawing_points(rows)
    assert len(points) == 2


def test_parse_element_rows_numeric_coercion():
    rows = read_csv_rows(
        b'StaStart,StaEnd,N,E,Azimuth,Radius,Type,Transition\r\n'
        b'0,100,1000,2000,90,0,T,\r\n'
    )
    out = parse_element_rows(rows)
    assert out[0] == ['StaStart', 'StaEnd', 'N', 'E', 'Azimuth', 'Radius', 'Type', 'Transition']
    assert out[1] == [0.0, 100.0, 1000.0, 2000.0, 90.0, 0.0, 'T', '']


def test_parse_element_rows_blank_radius_defaults_to_zero():
    rows = read_csv_rows(
        b'StaStart,StaEnd,N,E,Azimuth,Radius,Type,Transition\r\n'
        b'0,100,1000,2000,90,,T,\r\n'
    )
    out = parse_element_rows(rows)
    assert out[1][5] == 0.0
