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

_EMPTY_TABLE = """\
StaStart,StaEnd,N,E,Azimuth,Radius,Type,Transition
"""


@pytest.fixture
def table(tmp_path: Path) -> str:
    p = tmp_path / 'line.csv'
    p.write_text(_TABLE, encoding='utf-8')
    return str(p)


def test_fwd_centerline(table, capsys):
    rc = cli.main(['station-to-coord', table, '40'])
    assert rc == 0
    n_str, e_str = capsys.readouterr().out.strip().split(',')
    assert math.isclose(float(n_str), 1000.0, abs_tol=1e-6)
    assert math.isclose(float(e_str), 2040.0, abs_tol=1e-6)


def test_fwd_with_offset(table, capsys):
    # +10 offset = right of east-bound travel = south (N decreases by 10)
    rc = cli.main(['station-to-coord', table, '40', '--offset', '10'])
    assert rc == 0
    n_str, e_str = capsys.readouterr().out.strip().split(',')
    assert math.isclose(float(n_str), 990.0, abs_tol=1e-6)
    assert math.isclose(float(e_str), 2040.0, abs_tol=1e-6)


def test_inv_recovers_station_and_offset(table, capsys):
    # Point 10 south of sta=40 centre line -> sta=40, offset=+10.
    rc = cli.main(['coord-to-station', table, '990', '2040'])
    assert rc == 0
    sta_str, off_str = capsys.readouterr().out.strip().split(',')
    assert math.isclose(float(sta_str), 40.0, abs_tol=1e-3)
    assert math.isclose(float(off_str), 10.0, abs_tol=1e-3)


def test_fwd_inv_roundtrip(table, capsys):
    cli.main(['station-to-coord', table, '55', '--offset', '-7'])
    n_str, e_str = capsys.readouterr().out.strip().split(',')
    cli.main(['coord-to-station', table, n_str, e_str])
    sta_str, off_str = capsys.readouterr().out.strip().split(',')
    assert math.isclose(float(sta_str), 55.0, abs_tol=1e-3)
    assert math.isclose(float(off_str), -7.0, abs_tol=1e-3)


# ---------------------------------------------------------------------------
# Error-path tests: exit code 1 (04_coverage_docstring.txt §high-risk)
# ---------------------------------------------------------------------------

def test_missing_file_returns_exit_code_1(capsys):
    """Non-existent CSV file must produce exit code 1 and print to stderr."""
    rc = cli.main(['station-to-coord', 'nonexistent_file_xyz.csv', '40'])
    err = capsys.readouterr().err
    assert rc == 1
    assert 'error' in err.lower()


def test_fwd_station_outside_alignment_returns_exit_code_1(table, capsys):
    """Station beyond the alignment end must produce exit code 1."""
    # fixture table covers sta 0..100; sta=200 is outside
    rc = cli.main(['station-to-coord', table, '200'])
    err = capsys.readouterr().err
    assert rc == 1
    assert 'error' in err.lower()


def test_fwd_empty_csv_returns_exit_code_1(tmp_path, capsys):
    """Header-only CSV (0 elements) must produce exit code 1."""
    p = tmp_path / 'empty.csv'
    p.write_text(_EMPTY_TABLE, encoding='utf-8')
    rc = cli.main(['station-to-coord', str(p), '0'])
    err = capsys.readouterr().err
    assert rc == 1
    assert 'error' in err.lower()


# ---------------------------------------------------------------------------
# cross-check subcommand
# ---------------------------------------------------------------------------

_PI_TABLE = """\
POINT,N,E,Sta,R,Ls,LsIn,LsOut,Trans,Delta
BP,1000,2000,0,,,,,,
PI,1000,2500,,100,,,,,
EP,1500,2500,,,,,,,
"""

_FIELD_CSV = """\
NAME,N,E,Z,DISC
PT01,1000,2250,85.000,0.001
"""

_PI_TABLE_ANGLE = """\
POINT,N,E,Sta,R,Ls,LsIn,LsOut,Trans,Delta
BP,1000,2000,0,,,,,,
PI,1000,2500,,0,,,,,
EP,1500,2500,,,,,,,
"""


@pytest.fixture()
def pi_csv(tmp_path):
    p = tmp_path / 'pi.csv'
    p.write_text(_PI_TABLE, encoding='utf-8')
    return str(p)


@pytest.fixture()
def field_csv(tmp_path):
    p = tmp_path / 'field.csv'
    p.write_text(_FIELD_CSV, encoding='utf-8')
    return str(p)


def test_cross_check_basic(pi_csv, field_csv, capsys):
    rc = cli.main(['cross-check', pi_csv, field_csv])
    assert rc == 0
    out = capsys.readouterr().out
    assert 'NAME' in out
    assert 'STA' in out
    assert 'PT01' in out


def test_cross_check_missing_alignment(tmp_path, field_csv, capsys):
    rc = cli.main(['cross-check', str(tmp_path / 'no_such.csv'), field_csv])
    err = capsys.readouterr().err
    assert rc == 1
    assert 'error' in err.lower()


def test_cross_check_missing_field(pi_csv, tmp_path, capsys):
    rc = cli.main(['cross-check', pi_csv, str(tmp_path / 'no_such.csv')])
    err = capsys.readouterr().err
    assert rc == 1
    assert 'error' in err.lower()


def test_cross_check_angle_point_pi(tmp_path, field_csv, capsys):
    p = tmp_path / 'pi_angle.csv'
    p.write_text(_PI_TABLE_ANGLE, encoding='utf-8')
    rc = cli.main(['cross-check', str(p), field_csv])
    assert rc == 0
    out = capsys.readouterr().out
    assert 'PT01' in out


# ---------------------------------------------------------------------------
# build subcommand
# ---------------------------------------------------------------------------

def test_build_creates_output_files(pi_csv, tmp_path, capsys):
    rc = cli.main(['build', pi_csv, '--out-dir', str(tmp_path)])
    assert rc == 0
    assert (tmp_path / 'elements_output.csv').exists()
    assert (tmp_path / 'controls_so_output.csv').exists()


def test_build_element_csv_header(pi_csv, tmp_path, capsys):
    cli.main(['build', pi_csv, '--out-dir', str(tmp_path)])
    with open(tmp_path / 'elements_output.csv', encoding='utf-8') as f:
        header = f.readline().strip()
    assert header == 'StaStart,StaEnd,N,E,Azimuth,Radius,Type,Transition'


def test_build_control_csv_header(pi_csv, tmp_path, capsys):
    cli.main(['build', pi_csv, '--out-dir', str(tmp_path)])
    with open(tmp_path / 'controls_so_output.csv', encoding='utf-8') as f:
        header = f.readline().strip()
    assert header == 'Name,STA,N,E'


def test_build_terminal_output(pi_csv, tmp_path, capsys):
    cli.main(['build', pi_csv, '--out-dir', str(tmp_path)])
    out = capsys.readouterr().out
    assert 'Elements' in out
    assert 'Control Points' in out


def test_build_missing_input_returns_exit_1(tmp_path, capsys):
    rc = cli.main(['build', str(tmp_path / 'no_such.csv'), '--out-dir', str(tmp_path)])
    err = capsys.readouterr().err
    assert rc == 1
    assert 'error' in err.lower()


def test_build_default_out_dir(pi_csv, capsys):
    import os
    rc = cli.main(['build', pi_csv])
    assert rc == 0
    out_dir = os.path.dirname(os.path.abspath(pi_csv))
    assert os.path.exists(os.path.join(out_dir, 'elements_output.csv'))
    assert os.path.exists(os.path.join(out_dir, 'controls_so_output.csv'))


# ---------------------------------------------------------------------------
# compare-drawing subcommand
# ---------------------------------------------------------------------------

# east-bound tangent (table fixture): at sta=0 -> N=1000,E=2000; sta=80 -> N=1000,E=2080
_DRAWING_CSV = """\
Name,STA,N,E
BP,0,1000,2000
PI,50,1000,2050
CP1,80,1000,2080
"""


@pytest.fixture()
def drawing_csv(tmp_path: Path) -> str:
    p = tmp_path / 'drawing.csv'
    p.write_text(_DRAWING_CSV, encoding='utf-8')
    return str(p)


def test_compare_drawing_basic(table, drawing_csv, capsys):
    rc = cli.main(['compare-drawing', table, drawing_csv])
    assert rc == 0
    out = capsys.readouterr().out
    assert 'BP' in out
    assert 'PI' in out
    assert 'HIP' in out
    assert 'CP1' in out
    assert 'OK' in out


def test_compare_drawing_missing_file(table, capsys):
    rc = cli.main(['compare-drawing', table, 'no_such_drawing.csv'])
    err = capsys.readouterr().err
    assert rc == 1
    assert 'error' in err.lower()


def test_compare_drawing_hip_no_crash(table, tmp_path, capsys):
    p = tmp_path / 'hip.csv'
    p.write_text('Name,STA,N,E\nHIP,50,1000,2050\n', encoding='utf-8')
    rc = cli.main(['compare-drawing', table, str(p)])
    assert rc == 0
    out = capsys.readouterr().out
    assert 'HIP' in out


# ---------------------------------------------------------------------------
# fit-radius subcommand
# ---------------------------------------------------------------------------

def test_fit_radius_basic(pi_csv, drawing_csv, capsys):
    pytest.importorskip('scipy', reason='scipy not installed; pip install surveyor-micro-toolkit[optimize]')
    rc = cli.main(['fit-radius', pi_csv, drawing_csv])
    assert rc == 0
    out = capsys.readouterr().out
    assert 'gap_before' in out
    assert 'gap_after' in out


def test_fit_radius_missing_file(capsys):
    rc = cli.main(['fit-radius', 'no_such_pi.csv', 'no_such_drawing.csv'])
    err = capsys.readouterr().err
    assert rc == 1
    assert 'error' in err.lower()
