"""Input validation for the Lab 04 SPICE simulator.

The Lab 03 validator is intentionally left alone; this module only knows the
reference CE amplifier fields and their safe ranges.  Values arriving here are
already converted to base units (volts, ohms, farads, hertz) by ``app.py``.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass

from spice_engine import (
    ANALYSIS_AC,
    ANALYSIS_DC,
    ANALYSIS_TRAN,
    ANALYSES,
    SpiceInputs,
)

ANALYSIS_LABELS = {
    ANALYSIS_DC: "DC",
    ANALYSIS_AC: "AC",
    ANALYSIS_TRAN: "Transient",
}

ANALYSIS_CHOICES = tuple((key, ANALYSIS_LABELS[key]) for key in ANALYSES)

SPICE_FIELDS = (
    "vcc",
    "r1",
    "r2",
    "rc",
    "re",
    "rl",
    "cin",
    "cout",
    "amplitude",
    "frequency",
)

RESISTOR_FIELDS = ("r1", "r2", "rc", "re", "rl")
CAPACITOR_FIELDS = ("cin", "cout")

R_MIN = 1e-3
R_MAX = 10e6
C_MIN = 1e-12
C_MAX = 1.0
VCC_MAX = 100.0
AMPLITUDE_MAX = 1.0
FREQUENCY_MIN = 1.0
FREQUENCY_MAX = 10e6

ANALYSIS_ERROR = "Choose DC, AC or transient analysis."


@dataclass(frozen=True)
class FieldError:
    field: str
    message: str


def parse_analysis(raw: str | None) -> tuple[str | None, FieldError | None]:
    text = raw.strip() if isinstance(raw, str) else ""
    if not text:
        return ANALYSIS_DC, None
    if text in ANALYSES:
        return text, None
    return None, FieldError("analysis", ANALYSIS_ERROR)


def _read_number(
    form: Mapping[str, str],
    field: str,
    errors: list[FieldError],
) -> float | None:
    raw = form.get(field, "")
    text = raw.strip() if isinstance(raw, str) else str(raw).strip()

    if not text:
        errors.append(FieldError(field, "Required."))
        return None

    try:
        value = float(text)
    except ValueError:
        errors.append(FieldError(field, "Must be a number."))
        return None

    if not math.isfinite(value):
        errors.append(FieldError(field, "Must be a finite number."))
        return None

    return value


def parse_spice_inputs(
    form: Mapping[str, str],
) -> tuple[SpiceInputs | None, list[FieldError]]:
    errors: list[FieldError] = []
    values: dict[str, float] = {}

    for field in SPICE_FIELDS:
        value = _read_number(form, field, errors)
        if value is not None:
            values[field] = value

    if "vcc" in values and not (0.0 < values["vcc"] <= VCC_MAX):
        errors.append(
            FieldError("vcc", "Must be greater than 0 and at most 100 V.")
        )

    for field in RESISTOR_FIELDS:
        if field in values and not (R_MIN <= values[field] <= R_MAX):
            errors.append(
                FieldError(field, "Must be between 1 mΩ and 10 MΩ.")
            )

    for field in CAPACITOR_FIELDS:
        if field in values and not (C_MIN <= values[field] <= C_MAX):
            errors.append(
                FieldError(field, "Must be between 1 pF and 1 F.")
            )

    if "amplitude" in values and not (0.0 < values["amplitude"] <= AMPLITUDE_MAX):
        errors.append(
            FieldError(
                "amplitude",
                "Must be greater than 0 and at most 1 V peak.",
            )
        )

    if "frequency" in values and not (
        FREQUENCY_MIN <= values["frequency"] <= FREQUENCY_MAX
    ):
        errors.append(
            FieldError("frequency", "Must be between 1 Hz and 10 MHz.")
        )

    if errors:
        return None, errors

    return SpiceInputs(**values), []
