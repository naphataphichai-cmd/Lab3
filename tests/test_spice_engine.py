import math

import pytest

import spice_engine
from spice_engine import (
    ANALYSIS_AC,
    ANALYSIS_DC,
    ANALYSIS_TRAN,
    SpiceError,
    SpiceInputs,
    build_netlist,
    find_ngspice,
    parse_ac_table,
    parse_op_log,
    parse_tran_table,
    run,
)

BASELINE = SpiceInputs(
    vcc=12.0,
    r1=100e3,
    r2=22e3,
    rc=2.2e3,
    re=1e3,
    rl=10e3,
    cin=10e-6,
    cout=10e-6,
    amplitude=0.01,
    frequency=1e3,
)


def test_build_netlist_contains_reference_circuit():
    netlist = build_netlist(BASELINE, ANALYSIS_DC)

    assert "R1 vcc b 100000" in netlist
    assert "R2 b 0 22000" in netlist
    assert "RC vcc c 2200" in netlist
    assert "RE e 0 1000" in netlist
    assert "RL out 0 10000" in netlist
    assert "CIN in b 1e-05" in netlist
    assert "COUT c out 1e-05" in netlist
    assert "Q1 c b e 2N3904" in netlist
    assert ".model 2N3904 NPN(" in netlist
    assert "op" in netlist


def test_build_netlist_ac_uses_wrdata_and_source_sweep():
    netlist = build_netlist(BASELINE, ANALYSIS_AC)

    assert "ac dec 20 0.1 100000000" in netlist
    assert "wrdata ac.txt v(out)" in netlist
    assert "set wr_singlescale" in netlist


def test_build_netlist_transient_uses_five_cycles():
    netlist = build_netlist(BASELINE, ANALYSIS_TRAN)

    assert "tran 2.5e-06 0.005" in netlist
    assert "wrdata tran.txt v(in) v(out)" in netlist


def test_build_netlist_rejects_unknown_analysis():
    with pytest.raises(SpiceError):
        build_netlist(BASELINE, "noise")


def test_parse_op_log_reads_operating_point():
    log = """
v(b) = 2.003674e+00
v(e) = 1.332880e+00
v(c) = 9.087216e+00
v(b)-v(e) = 6.707948e-01
@q1[ic] = 1.324035e-03
@q1[ib] = 8.887366e-06
"""

    op = parse_op_log(log)

    assert op.vb == pytest.approx(2.003674)
    assert op.ve == pytest.approx(1.332880)
    assert op.vc == pytest.approx(9.087216)
    assert op.vce == pytest.approx(7.754336)
    assert op.ic == pytest.approx(1.324035e-3)
    assert op.ib == pytest.approx(8.887366e-6)
    assert op.ie == pytest.approx(op.ic + op.ib)


def test_parse_op_log_rejects_missing_values():
    with pytest.raises(SpiceError):
        parse_op_log("v(b) = 2.0")


def test_parse_ac_table_computes_magnitude_and_phase():
    text = """ frequency v(out) v(out)
 1.00000000e+03 -1.75458163e+00 6.03031038e-02
 1.00000000e+04 -1.75000000e+00 0.00000000e+00
"""

    points = parse_ac_table(text)

    assert len(points) == 2
    assert points[0].frequency == pytest.approx(1e3)
    assert points[0].gain_mag == pytest.approx(math.hypot(1.75458163, 0.0603031038))
    assert points[0].gain_db == pytest.approx(
        20 * math.log10(math.hypot(1.75458163, 0.0603031038))
    )
    assert points[0].phase_deg > 170


def test_parse_ac_table_rejects_empty_data():
    with pytest.raises(SpiceError):
        parse_ac_table(" frequency v(out) v(out)\n")


def test_parse_tran_table_reads_waveforms():
    text = """ time v(in) v(out)
 0.00000000e+00 0.00000000e+00 0.00000000e+00
 1.00000000e-06 6.28318489e-05 -1.22203276e-04
"""

    points = parse_tran_table(text)

    assert len(points) == 2
    assert points[1].time == pytest.approx(1e-6)
    assert points[1].vin == pytest.approx(6.28318489e-5)
    assert points[1].vout == pytest.approx(-1.22203276e-4)


def test_parse_tran_table_rejects_empty_data():
    with pytest.raises(SpiceError):
        parse_tran_table(" time v(in) v(out)\n")


def test_find_ngspice_uses_local_tools_install():
    path = find_ngspice()
    assert path


def test_run_rejects_missing_executable():
    with pytest.raises(SpiceError):
        run(BASELINE, ANALYSIS_DC, ngspice_path="definitely-not-ngspice")


def test_run_dc_against_real_ngspice():
    if not spice_engine.ngspice_available():
        pytest.skip("ngspice is not installed")

    result = run(BASELINE, ANALYSIS_DC)

    assert result.analysis == ANALYSIS_DC
    assert result.engine.startswith("ngspice-")
    assert result.model == "2N3904"
    assert "R1 vcc b 100000" in result.netlist
    assert result.op is not None
    assert math.isfinite(result.op.ic)
    assert result.op.ic > 0
    assert 0 < result.op.vce < 12


def test_run_ac_against_real_ngspice():
    if not spice_engine.ngspice_available():
        pytest.skip("ngspice is not installed")

    result = run(BASELINE, ANALYSIS_AC)

    assert result.analysis == ANALYSIS_AC
    assert len(result.ac) > 50
    nearest = min(result.ac, key=lambda point: abs(point.frequency - 1e3))
    assert 3 < nearest.gain_db < 7
    assert abs(nearest.phase_deg) > 90


def test_run_tran_against_real_ngspice():
    if not spice_engine.ngspice_available():
        pytest.skip("ngspice is not installed")

    result = run(BASELINE, ANALYSIS_TRAN)

    assert result.analysis == ANALYSIS_TRAN
    assert len(result.tran) > 100
    vin = [point.vin for point in result.tran]
    vout = [point.vout for point in result.tran]
    assert max(vin) > 0.009
    assert min(vin) < -0.009
    assert max(vout) > 0.009
    assert min(vout) < -0.009
