import pytest

import spice_engine
from spice_engine import AcPoint, OperatingPoint, SpiceResult, TranPoint


def spice_form(**overrides):
    form = {
        "analysis": "dc",
        "vcc": "12",
        "vcc_unit": "V",
        "r1": "100",
        "r1_unit": "kΩ",
        "r2": "22",
        "r2_unit": "kΩ",
        "rc": "2.2",
        "rc_unit": "kΩ",
        "re": "1.0",
        "re_unit": "kΩ",
        "rl": "10",
        "rl_unit": "kΩ",
        "cin": "10",
        "cin_unit": "µF",
        "cout": "10",
        "cout_unit": "µF",
        "amplitude": "10",
        "amplitude_unit": "mV",
        "frequency": "1",
        "frequency_unit": "kHz",
    }
    form.update(overrides)
    return form


def dc_result(inputs, analysis="dc"):
    return SpiceResult(
        analysis=analysis,
        inputs=inputs,
        model="2N3904",
        engine="ngspice-47",
        netlist="* generated netlist\nQ1 c b e 2N3904",
        log="v(b) = 2.0\nv(e) = 1.3\nv(c) = 9.0\n@q1[ic] = 1.3e-3\n@q1[ib] = 8.9e-6",
        op=OperatingPoint(
            vb=2.0,
            ve=1.3,
            vc=9.0,
            vce=0.7,
            ic=1.3e-3,
            ib=8.9e-6,
            ie=1.3089e-3,
        ),
    )


def test_simulator_get_renders_controls(client):
    response = client.get("/simulator")
    text = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Lab 04" in text
    assert "DC" in text
    assert "AC" in text
    assert "Transient" in text
    assert "Run simulation" in text
    assert "ngspice" in text
    assert "Lab 03" in text


def test_simulator_post_dc_uses_engine_and_shows_spice_results(client, monkeypatch):
    calls = []

    def fake_run(inputs, analysis, **kwargs):
        calls.append((inputs, analysis))
        return dc_result(inputs, analysis)

    monkeypatch.setattr(spice_engine, "run", fake_run)

    response = client.post("/simulator", data=spice_form())
    text = response.get_data(as_text=True)

    assert response.status_code == 200
    assert calls and calls[0][1] == "dc"
    assert calls[0][0].r1 == pytest.approx(100e3)
    assert "SUCCESS" in text
    assert "2N3904" in text
    assert "ngspice-47" in text
    assert "1.3 mA" in text
    assert "1.309 mA" in text
    assert "Lab 03 analytical reference" in text
    assert "* generated netlist" in text


def test_simulator_post_validation_error_does_not_run_engine(client, monkeypatch):
    called = False

    def fake_run(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("engine must not run for invalid input")

    monkeypatch.setattr(spice_engine, "run", fake_run)

    response = client.post("/simulator", data=spice_form(re="0"))
    text = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Must be between 1 mΩ and 10 MΩ." in text
    assert not called
    assert "SUCCESS" not in text


def test_simulator_post_engine_error_is_visible(client, monkeypatch):
    def fake_run(*args, **kwargs):
        raise spice_engine.SpiceError("ngspice was not found. Install ngspice.")

    monkeypatch.setattr(spice_engine, "run", fake_run)

    response = client.post("/simulator", data=spice_form())
    text = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "ngspice was not found. Install ngspice." in text
    assert "SUCCESS" not in text


def test_simulator_post_ac_renders_bode_plot(client, monkeypatch):
    def fake_run(inputs, analysis, **kwargs):
        return SpiceResult(
            analysis=analysis,
            inputs=inputs,
            model="2N3904",
            engine="ngspice-47",
            netlist="* ac netlist",
            log="No. of Data Rows : 101",
            ac=(
                AcPoint(frequency=10, gain_mag=1.0, gain_db=0.0, phase_deg=-170),
                AcPoint(frequency=100, gain_mag=1.78, gain_db=5.0, phase_deg=-180),
                AcPoint(frequency=1000, gain_mag=1.78, gain_db=5.0, phase_deg=180),
                AcPoint(frequency=10000, gain_mag=1.0, gain_db=0.0, phase_deg=170),
            ),
            sweep_start=10,
            sweep_stop=100000,
        )

    monkeypatch.setattr(spice_engine, "run", fake_run)

    response = client.post("/simulator", data=spice_form(analysis="ac"))
    text = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Bode" in text
    assert "Gain at 1 kHz" in text
    assert "Phase at 1 kHz" in text
    assert "<svg" in text
    assert "Frequency (Hz)" in text


def test_simulator_post_tran_renders_waveform(client, monkeypatch):
    def fake_run(inputs, analysis, **kwargs):
        return SpiceResult(
            analysis=analysis,
            inputs=inputs,
            model="2N3904",
            engine="ngspice-47",
            netlist="* tran netlist",
            log="No. of Data Rows : 508",
            tran=(
                TranPoint(time=0.0, vin=0.0, vout=0.0),
                TranPoint(time=0.001, vin=0.01, vout=-0.017),
                TranPoint(time=0.002, vin=-0.01, vout=0.017),
            ),
            tran_stop=0.005,
        )

    monkeypatch.setattr(spice_engine, "run", fake_run)

    response = client.post("/simulator", data=spice_form(analysis="tran"))
    text = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Transient" in text
    assert "Vin peak-to-peak" in text
    assert "Vout peak-to-peak" in text
    assert "inverted" in text
    assert "Time (ms)" in text


def fixed_form(**overrides):
    form = {
        "mode": "fixed",
        "analysis": "dc",
        "vcc": "12",
        "vcc_unit": "V",
        "rb": "1",
        "rb_unit": "MΩ",
        "rc": "2.2",
        "rc_unit": "kΩ",
        "rl": "10",
        "rl_unit": "kΩ",
        "cin": "10",
        "cin_unit": "µF",
        "cout": "10",
        "cout_unit": "µF",
        "amplitude": "10",
        "amplitude_unit": "mV",
        "frequency": "1",
        "frequency_unit": "kHz",
    }
    form.update(overrides)
    return form


def emitter_form(**overrides):
    form = fixed_form()
    form.update({"mode": "emitter", "re": "1", "re_unit": "kΩ"})
    form.update(overrides)
    return form


def test_simulator_get_fixed_shows_rb_and_hides_divider_fields(client):
    response = client.get("/simulator?mode=fixed")
    text = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Fixed Bias" in text
    assert "RB (Base Resistor)" in text
    assert "R1 (upper divider)" not in text
    assert "R2 (lower divider)" not in text
    assert "RE (emitter)" not in text


def test_simulator_get_emitter_shows_rb_and_re(client):
    response = client.get("/simulator?mode=emitter")
    text = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Emitter Bias" in text
    assert "RB (Base Resistor)" in text
    assert "RE (emitter)" in text
    assert "R1 (upper divider)" not in text


def test_simulator_post_fixed_passes_mode_and_uses_fixed_reference(client, monkeypatch):
    calls = []

    def fake_run(inputs, analysis, **kwargs):
        calls.append((inputs, analysis))
        return dc_result(inputs, analysis)

    monkeypatch.setattr(spice_engine, "run", fake_run)

    response = client.post("/simulator", data=fixed_form())
    text = response.get_data(as_text=True)

    assert response.status_code == 200
    assert calls[0][0].mode == "fixed"
    assert calls[0][0].rb == pytest.approx(1e6)
    assert "SUCCESS" in text
    assert "Fixed Bias" in text
    assert "Lab 03 analytical reference" in text
    assert "1.13 mA" in text


def test_simulator_post_emitter_passes_mode_and_uses_emitter_reference(client, monkeypatch):
    calls = []

    def fake_run(inputs, analysis, **kwargs):
        calls.append((inputs, analysis))
        return dc_result(inputs, analysis)

    monkeypatch.setattr(spice_engine, "run", fake_run)

    response = client.post("/simulator", data=emitter_form())
    text = response.get_data(as_text=True)

    assert response.status_code == 200
    assert calls[0][0].mode == "emitter"
    assert calls[0][0].re == pytest.approx(1e3)
    assert "Emitter Bias" in text
    assert "1.026 mA" in text


def test_simulator_post_invalid_mode_does_not_run_engine(client, monkeypatch):
    called = False

    def fake_run(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("engine must not run for an invalid mode")

    monkeypatch.setattr(spice_engine, "run", fake_run)

    response = client.post("/simulator", data=fixed_form(mode="noise"))
    text = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Choose a supported circuit mode." in text
    assert not called
    assert "SUCCESS" not in text


def test_simulator_mode_selector_preserves_analysis(client):
    response = client.get("/simulator?mode=fixed&analysis=ac")
    text = response.get_data(as_text=True)

    assert 'name="mode"' in text
    assert 'name="analysis"' in text
    assert "Fixed Bias" in text
    assert "AC" in text


def test_simulator_get_divider_keeps_original_fields(client):
    response = client.get("/simulator?mode=divider")
    text = response.get_data(as_text=True)

    assert "R1 (upper divider)" in text
    assert "R2 (lower divider)" in text
    assert "RE (emitter)" in text
    assert "RB (Base Resistor)" not in text
