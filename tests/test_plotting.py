from plotting import bode_svg, format_si, transient_svg
from spice_engine import AcPoint, TranPoint


def test_format_si_uses_engineering_prefixes():
    assert format_si(1000) == "1 k"
    assert format_si(0.001) == "1 m"
    assert format_si(2.5e-6) == "2.5 µ"
    assert format_si(12) == "12"


def test_bode_svg_has_two_panels_and_axis_labels():
    points = (
        AcPoint(frequency=10, gain_mag=1.0, gain_db=0.0, phase_deg=-170),
        AcPoint(frequency=100, gain_mag=1.78, gain_db=5.0, phase_deg=-180),
        AcPoint(frequency=1000, gain_mag=3.16, gain_db=10.0, phase_deg=-175),
    )

    svg = bode_svg(points)

    assert svg.startswith("<svg")
    assert svg.endswith("</svg>")
    assert 'aria-label="AC Bode plot"' in svg
    assert "Frequency (Hz)" in svg
    assert "Gain (dB)" in svg
    assert "Phase (deg)" in svg
    assert svg.count("<polyline") == 2
    assert "10" in svg and "1 k" in svg


def test_transient_svg_has_two_waveforms_and_legend():
    points = (
        TranPoint(time=0.0, vin=0.0, vout=0.0),
        TranPoint(time=0.001, vin=0.01, vout=-0.017),
        TranPoint(time=0.002, vin=-0.01, vout=0.017),
    )

    svg = transient_svg(points)

    assert svg.startswith("<svg")
    assert 'aria-label="Transient waveform"' in svg
    assert "Time (ms)" in svg
    assert "Voltage (mV)" in svg
    assert "Vin" in svg
    assert "Vout" in svg
    assert svg.count("<polyline") == 2


def test_bode_svg_unwraps_phase_wrap():
    points = (
        AcPoint(frequency=10, gain_mag=1.0, gain_db=0.0, phase_deg=179),
        AcPoint(frequency=100, gain_mag=1.0, gain_db=0.0, phase_deg=-179),
        AcPoint(frequency=1000, gain_mag=1.0, gain_db=0.0, phase_deg=-178),
    )

    svg = bode_svg(points)

    assert "Phase (deg)" in svg
    assert svg.count("<polyline") == 2
