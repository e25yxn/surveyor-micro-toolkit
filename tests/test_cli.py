"""Tests for smt.cli — the minimal command-line interface.

Uses a tiny self-contained CSV element table written into a tmp file, then
exercises both subcommands through cli.main(), capturing stdout.

The fixture is a single tangent running due east from (1000, 2000):
  StaStart=0, StaEnd=100, N=1000, E=2000, Azimuth=90, Radius=0, Type=T
So at sta=40, offset=0  -> N=1000, E=2040 (east of start).
A +10 offset (right of east-bound travel) points south -> N=990.
"""
import math
from pathlib import Path

import pytest

from smt import cli

_TABLE = """\
StaStart,StaEnd,N,E,Azimuth,Radius,Type,Transition
0,100,1000,2000,90,0,T,
"""


@pytest.fixture
def table(tmp_path: Path) -> str:
    p = tmp_path / 'line.csv'
    p.write_text(_TABLE, encoding='utf-8')
    return str(p)


def test_fwd_centerline(table, capsys):
    rc = cli.main(['fwd', table, '40'])
    assert rc == 0
    n_str, e_str = capsys.readouterr().out.strip().split(',')
    assert math.isclose(float(n_str), 1000.0, abs_tol=1e-6)
    assert math.isclose(float(e_str), 2040.0, abs_tol=1e-6)


def test_fwd_with_offset(table, capsys):
    # +10 offset = right of east-bound travel = south (N decreases by 10)
    rc = cli.main(['fwd', table, '40', '--offset', '10'])
    assert rc == 0
    n_str, e_str = capsys.readouterr().out.strip().split(',')
    assert math.isclose(float(n_str), 990.0, abs_tol=1e-6)
    assert math.isclose(float(e_str), 2040.0, abs_tol=1e-6)


def test_inv_recovers_station_and_offset(table, capsys):
    # Point 10 south of sta=40 centre line -> sta=40, offset=+10.
    rc = cli.main(['inv', table, '990', '2040'])
    assert rc == 0
    sta_str, off_str = capsys.readouterr().out.strip().split(',')
    assert math.isclose(float(sta_str), 40.0, abs_tol=1e-3)
    assert math.isclose(float(off_str), 10.0, abs_tol=1e-3)


def test_fwd_inv_roundtrip(table, capsys):
    cli.main(['fwd', table, '55', '--offset', '-7'])
    n_str, e_str = capsys.readouterr().out.strip().split(',')
    cli.main(['inv', table, n_str, e_str])
    sta_str, off_str = capsys.readouterr().out.strip().split(',')
    assert math.isclose(float(sta_str), 55.0, abs_tol=1e-3)
    assert math.isclose(float(off_str), -7.0, abs_tol=1e-3)
