import pytest

from spice_engine import SpiceInputs
from spice_validation import (
    CIRCUIT_FIELDS,
    FieldError,
    parse_analysis,
    parse_circuit,
    parse_spice_inputs,
)


def baseline_form(**overrides):
    form = {
        "vcc": "12",
        "r1": "100000",
        "r2": "22000",
        "rc": "2200",
        "re": "1000",
        "rl": "10000",
        "cin": "0.00001",
        "cout": "0.00001",
        "amplitude": "0.01",
        "frequency": "1000",
    }
    form.update(overrides)
    return form


def test_parse_spice_inputs_accepts_baseline():
    inputs, errors = parse_spice_inputs(baseline_form())

    assert errors == []
    assert isinstance(inputs, SpiceInputs)
    assert inputs.vcc == 12
    assert inputs.r1 == 100000
    assert inputs.cin == pytest.approx(1e-5)
    assert inputs.frequency == 1000


def test_parse_spice_inputs_rejects_zero_re():
    inputs, errors = parse_spice_inputs(baseline_form(re="0"))

    assert inputs is None
    assert any(error.field == "re" for error in errors)


def test_parse_spice_inputs_rejects_negative_amplitude():
    inputs, errors = parse_spice_inputs(baseline_form(amplitude="-0.01"))

    assert inputs is None
    assert any(error.field == "amplitude" for error in errors)


def test_parse_spice_inputs_rejects_zero_frequency():
    inputs, errors = parse_spice_inputs(baseline_form(frequency="0"))

    assert inputs is None
    assert any(error.field == "frequency" for error in errors)


def test_parse_spice_inputs_rejects_missing_field():
    form = baseline_form()
    del form["rc"]

    inputs, errors = parse_spice_inputs(form)

    assert inputs is None
    assert any(error.field == "rc" and error.message == "Required." for error in errors)


def test_parse_spice_inputs_rejects_non_numeric():
    inputs, errors = parse_spice_inputs(baseline_form(vcc="twelve"))

    assert inputs is None
    assert any(error.field == "vcc" for error in errors)


def test_parse_analysis_defaults_to_dc():
    analysis, error = parse_analysis(None)

    assert analysis == "dc"
    assert error is None


def test_parse_analysis_accepts_all_three():
    assert parse_analysis("dc") == ("dc", None)
    assert parse_analysis("ac") == ("ac", None)
    assert parse_analysis("tran") == ("tran", None)


def test_parse_analysis_rejects_unknown():
    analysis, error = parse_analysis("noise")

    assert analysis is None
    assert isinstance(error, FieldError)
    assert error.field == "analysis"


def fixed_form(**overrides):
    form = {
        "vcc": "12",
        "rb": "1000000",
        "rc": "2200",
        "rl": "10000",
        "cin": "0.00001",
        "cout": "0.00001",
        "amplitude": "0.01",
        "frequency": "1000",
    }
    form.update(overrides)
    return form


def emitter_form(**overrides):
    form = fixed_form()
    form["re"] = "1000"
    form.update(overrides)
    return form


def test_parse_circuit_defaults_to_divider():
    assert parse_circuit(None) == ("divider", None)


@pytest.mark.parametrize("mode", ["divider", "fixed", "emitter"])
def test_parse_circuit_accepts_supported_modes(mode):
    assert parse_circuit(mode) == (mode, None)


def test_parse_circuit_rejects_unknown_mode():
    mode, error = parse_circuit("noise")

    assert mode is None
    assert error is not None
    assert error.field == "mode"


def test_parse_spice_inputs_fixed_accepts_rb_without_divider_fields():
    inputs, errors = parse_spice_inputs(fixed_form(), mode="fixed")

    assert errors == []
    assert inputs is not None
    assert inputs.mode == "fixed"
    assert inputs.rb == 1e6
    assert inputs.r1 is None
    assert inputs.re is None


def test_parse_spice_inputs_fixed_rejects_zero_rb():
    inputs, errors = parse_spice_inputs(fixed_form(rb="0"), mode="fixed")

    assert inputs is None
    assert any(error.field == "rb" for error in errors)


def test_parse_spice_inputs_emitter_requires_re():
    form = fixed_form()
    inputs, errors = parse_spice_inputs(form, mode="emitter")

    assert inputs is None
    assert any(error.field == "re" for error in errors)


def test_parse_spice_inputs_divider_still_requires_r1():
    form = baseline_form()
    del form["r1"]
    inputs, errors = parse_spice_inputs(form)

    assert inputs is None
    assert any(error.field == "r1" for error in errors)


def test_parse_spice_inputs_ignores_irrelevant_fields():
    form = fixed_form(r1="0", r2="0", re="0")
    inputs, errors = parse_spice_inputs(form, mode="fixed")

    assert errors == []
    assert inputs is not None
    assert inputs.mode == "fixed"
