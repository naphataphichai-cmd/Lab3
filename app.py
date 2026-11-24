import math

from flask import Flask, render_template, request

import plotting
import spice_engine
import spice_validation
from engineering import evaluate, format as fmt, model, validation

DEFAULT_FORM = {
    "mode": model.MODE_DIVIDER,
    "vcc": "12",
    "r1": "100",
    "r2": "22",
    "rb": "1",
    "rc": "2.2",
    "re": "1.0",
    "beta": "100",
    "vbe": "0.70",
}

RESISTOR_UNITS = ("Ω", "kΩ", "MΩ")
VOLTAGE_UNITS = ("V", "mV")
CAPACITOR_UNITS = ("pF", "nF", "µF", "F")
FREQUENCY_UNITS = ("Hz", "kHz", "MHz")

DEFAULT_UNITS = {
    "vcc": "V",
    "r1": "kΩ",
    "r2": "kΩ",
    "rb": "MΩ",
    "rc": "kΩ",
    "re": "kΩ",
    "vbe": "V",
}

UNIT_SCALE = {
    "Ω": 1.0,
    "kΩ": 1e3,
    "MΩ": 1e6,
    "V": 1.0,
    "mV": 1e-3,
    "pF": 1e-12,
    "nF": 1e-9,
    "µF": 1e-6,
    "F": 1.0,
    "Hz": 1.0,
    "kHz": 1e3,
    "MHz": 1e6,
}

UNIT_CHOICES = {
    "vcc": VOLTAGE_UNITS,
    "r1": RESISTOR_UNITS,
    "r2": RESISTOR_UNITS,
    "rb": RESISTOR_UNITS,
    "rc": RESISTOR_UNITS,
    "re": RESISTOR_UNITS,
    "vbe": VOLTAGE_UNITS,
}

MODE_CHOICES = [(mode, model.MODE_LABELS[mode]) for mode in model.MODES]

SPICE_DEFAULT_FORM = {
    "analysis": spice_engine.ANALYSIS_DC,
    "vcc": "12",
    "r1": "100",
    "r2": "22",
    "rc": "2.2",
    "re": "1.0",
    "rl": "10",
    "cin": "10",
    "cout": "10",
    "amplitude": "10",
    "frequency": "1",
}

SPICE_DEFAULT_UNITS = {
    "vcc": "V",
    "r1": "kΩ",
    "r2": "kΩ",
    "rc": "kΩ",
    "re": "kΩ",
    "rl": "kΩ",
    "cin": "µF",
    "cout": "µF",
    "amplitude": "mV",
    "frequency": "kHz",
}

SPICE_UNIT_CHOICES = {
    "vcc": VOLTAGE_UNITS,
    "r1": RESISTOR_UNITS,
    "r2": RESISTOR_UNITS,
    "rc": RESISTOR_UNITS,
    "re": RESISTOR_UNITS,
    "rl": RESISTOR_UNITS,
    "cin": CAPACITOR_UNITS,
    "cout": CAPACITOR_UNITS,
    "amplitude": VOLTAGE_UNITS,
    "frequency": FREQUENCY_UNITS,
}

SPICE_REFERENCE_BETA = 100.0
SPICE_REFERENCE_VBE = 0.70

# Lab 03 acceptance record shown on the page. Expected values were calculated
# by hand from the bias equations before the app was run; observed values are
# what the in-app browser showed for each case.
ACCEPTANCE_CASES = (
    {
        "id": "A1",
        "title": "Original mode",
        "inputs": "Divider · R1 = 100 kΩ, R2 = 22 kΩ, RE = 1 kΩ",
        "expected": "IC = 1.2298 mA · VCE = 8.0522 V (same as Lab 02)",
        "observed": "IC = 1.23 mA · VCE = 8.052 V",
        "method": "OpenCode Browser",
        "status": "PASS",
    },
    {
        "id": "A2",
        "title": "Fixed",
        "inputs": "Fixed · RB = 1 MΩ",
        "expected": "IC = 1.1300 mA · VCE = 9.5140 V; no RE input needed",
        "observed": "IC = 1.13 mA · VCE = 9.514 V",
        "method": "OpenCode Browser",
        "status": "PASS",
    },
    {
        "id": "A3",
        "title": "Emitter",
        "inputs": "Emitter · RB = 1 MΩ, RE = 1 kΩ",
        "expected": "IC = 1.0263 mA · VCE = 8.7054 V; RE field used",
        "observed": "IC = 1.026 mA · VCE = 8.705 V",
        "method": "OpenCode Browser",
        "status": "PASS",
    },
    {
        "id": "A4",
        "title": "One value changed",
        "inputs": "Emitter · as A3 with RE = 2 kΩ",
        "expected": "IC must fall from A3: IC = 0.9401 mA · VCE = 8.0328 V",
        "observed": "IC = 940.1 µA · VCE = 8.033 V (lower than A3)",
        "method": "OpenCode Browser",
        "status": "PASS",
    },
    {
        "id": "A5",
        "title": "Bad input",
        "inputs": "Fixed · RB = 0",
        "expected": "Message for RB, page stays up, no previous result reused",
        "observed": "“Must be between 1 mΩ and 10 MΩ.”; result table shows --",
        "method": "OpenCode Browser",
        "status": "PASS",
    },
)


RESULT_ROWS = (
    ("VB", "vb", "voltage"),
    ("VE", "ve", "voltage"),
    ("VC", "vc", "voltage"),
    ("VCE", "vce", "voltage"),
    ("IB", "ib", "current"),
    ("IC", "ic", "current"),
    ("IE", "ie", "current"),
)

FORMATTERS = {
    "current": fmt.format_current,
    "voltage": fmt.format_voltage,
}


def _with_unit(kind: str, value: float) -> str:
    number, unit = FORMATTERS[kind](value)
    return f"{number} {unit}"


def _selected_units(
    form,
    defaults: dict[str, str] | None = None,
    choices: dict[str, tuple[str, ...]] | None = None,
) -> dict[str, str]:
    defaults = DEFAULT_UNITS if defaults is None else defaults
    choices = UNIT_CHOICES if choices is None else choices
    units = {}
    for field, fallback in defaults.items():
        chosen = form.get(f"{field}_unit", fallback)
        allowed = choices.get(field, ())
        units[field] = chosen if chosen in allowed else fallback
    return units


def _to_base_units(
    form,
    units: dict[str, str],
    fields,
    unit_choices: dict[str, tuple[str, ...]] | None = None,
) -> dict[str, str]:
    """Convert the submitted values to base units for the engineering layer."""
    unit_choices = UNIT_CHOICES if unit_choices is None else unit_choices
    scaled: dict[str, str] = {}

    for field in fields:
        raw = form.get(field, "")
        text = raw.strip() if isinstance(raw, str) else str(raw).strip()

        if not text or field not in unit_choices:
            scaled[field] = text
            continue

        try:
            value = float(text) * UNIT_SCALE[units[field]]
        except (ValueError, OverflowError):
            scaled[field] = text
            continue

        scaled[field] = f"{value:.12g}"

    return scaled


def _build_view(evaluation: evaluate.Evaluation) -> dict:
    rows = []
    for symbol, field, kind in RESULT_ROWS:
        analytical = getattr(evaluation.analytical, field)
        independent = getattr(evaluation.independent, field)
        rows.append(
            {
                "symbol": symbol,
                "analytical": _with_unit(kind, analytical),
                "independent": _with_unit(kind, independent),
                "delta": _with_unit(kind, abs(analytical - independent)),
            }
        )

    mode = evaluation.mode
    view = {
        "region": evaluation.region,
        "comparison": evaluation.comparison,
        "rows": rows,
        "mode": mode,
        "mode_label": model.MODE_LABELS[mode],
        "show_supporting": mode == model.MODE_DIVIDER,
        "max_error": fmt.format_error(evaluation.comparison.max_rel_error),
    }

    if view["show_supporting"]:
        vbb_number, vbb_unit = fmt.format_voltage(evaluation.analytical.vbb)
        rb_number, rb_unit = fmt.format_resistance(evaluation.analytical.rb)
        view["vbb"] = f"{vbb_number} {vbb_unit}"
        view["rb"] = f"{rb_number} {rb_unit}"

    return view


def _spice_region(op) -> str:
    if op.ic <= 0.0:
        return "cutoff"
    if op.vce <= 0.2:
        return "saturation"
    return "active"


def _cutoff_frequencies(points, midband_db: float):
    target = midband_db - 3.0
    first = None
    last = None
    for index, point in enumerate(points):
        if point.gain_db >= target:
            if first is None:
                first = index
            last = index

    if first is None:
        return None, None

    low = points[first].frequency if first > 0 else None
    high = points[last].frequency if last < len(points) - 1 else None
    return low, high


def _build_simulator_view(result: spice_engine.SpiceResult, inputs) -> dict:
    spice_rows = []
    delta_rows = []
    if result.op is not None:
        for symbol, field, kind in RESULT_ROWS:
            spice_rows.append(
                {"symbol": symbol, "value": _with_unit(kind, getattr(result.op, field))}
            )

    analytical_rows = []
    analytical_region = None
    analytical_note = (
        "Lab 03 analytical reference: β = 100, VBE = 0.70 V. "
        "SPICE uses the 2N3904 model, so the two DC results need not match "
        "digit for digit."
    )
    try:
        reference = model.BiasInputs(
            vcc=inputs.vcc,
            r1=inputs.r1,
            r2=inputs.r2,
            rc=inputs.rc,
            re=inputs.re,
            beta=SPICE_REFERENCE_BETA,
            vbe=SPICE_REFERENCE_VBE,
        )
        evaluation = evaluate.evaluate(reference, model.MODE_DIVIDER)
        analytical_region = evaluation.region.name
        for symbol, field, kind in RESULT_ROWS:
            analytical_rows.append(
                {
                    "symbol": symbol,
                    "value": _with_unit(kind, getattr(evaluation.analytical, field)),
                }
            )
        if result.op is not None:
            for symbol, field, kind in RESULT_ROWS:
                difference = abs(
                    getattr(result.op, field) - getattr(evaluation.analytical, field)
                )
                delta_rows.append(
                    {"symbol": symbol, "value": _with_unit(kind, difference)}
                )
    except (ValueError, ZeroDivisionError, OverflowError):
        analytical_note = (
            "Lab 03 analytical reference is not available for these inputs."
        )

    metrics = [
        {"label": "Run status", "value": "SUCCESS"},
        {"label": "Analysis", "value": spice_engine.ANALYSIS_LABELS[result.analysis]},
        {"label": "Engine", "value": result.engine},
        {"label": "Model", "value": result.model},
    ]

    spice_region = None
    if result.op is not None:
        spice_region = _spice_region(result.op)
        metrics.append({"label": "SPICE region", "value": spice_region})

    plot_svg = None
    plot_caption = "DC analysis returns one operating point; see the results panel."
    source_text = (
        f"{plotting.format_si(inputs.amplitude, 'V')} peak · "
        f"{plotting.format_si(inputs.frequency, 'Hz')}"
    )

    if result.analysis == spice_engine.ANALYSIS_AC:
        nearest = min(
            result.ac,
            key=lambda point: abs(math.log10(point.frequency / inputs.frequency)),
        )
        source_label = plotting.format_si(inputs.frequency, "Hz")
        midband = max(point.gain_db for point in result.ac)
        low, high = _cutoff_frequencies(result.ac, midband)

        metrics.extend(
            [
                {
                    "label": f"Gain at {source_label}",
                    "value": f"{nearest.gain_db:.2f} dB ({nearest.gain_mag:.3f}×)",
                },
                {
                    "label": f"Phase at {source_label}",
                    "value": f"{nearest.phase_deg:.1f}°",
                },
                {"label": "Midband gain", "value": f"{midband:.2f} dB"},
            ]
        )

        if low is None and high is None:
            cutoff_text = "not determined in sweep range"
        elif low is None:
            cutoff_text = f"fH ≈ {plotting.format_si(high, 'Hz')}; fL not in sweep"
        elif high is None:
            cutoff_text = f"fL ≈ {plotting.format_si(low, 'Hz')}; fH not in sweep"
        else:
            cutoff_text = (
                f"fL ≈ {plotting.format_si(low, 'Hz')} / "
                f"fH ≈ {plotting.format_si(high, 'Hz')}"
            )
        metrics.append({"label": "−3 dB points", "value": cutoff_text})
        metrics.append(
            {
                "label": "Sweep",
                "value": (
                    f"{plotting.format_si(result.sweep_start, 'Hz')} – "
                    f"{plotting.format_si(result.sweep_stop, 'Hz')}"
                ),
            }
        )
        plot_svg = plotting.bode_svg(result.ac)
        plot_caption = (
            "Bode response from the ngspice .ac run. Gain reference: source "
            "node in (AC 1 V, 0°); output: node out across RL."
        )

    elif result.analysis == spice_engine.ANALYSIS_TRAN:
        tail = result.tran[max(int(len(result.tran) * 0.2), 0) :]
        vin_pp = max(point.vin for point in tail) - min(point.vin for point in tail)
        vout_pp = max(point.vout for point in tail) - min(point.vout for point in tail)
        gain = vout_pp / vin_pp if vin_pp > 0 else 0.0
        dot = sum(point.vin * point.vout for point in tail)
        inverted = dot < 0
        metrics.extend(
            [
                {"label": "Vin peak-to-peak", "value": plotting.format_si(vin_pp, "V")},
                {"label": "Vout peak-to-peak", "value": plotting.format_si(vout_pp, "V")},
                {"label": "Vout/Vin", "value": f"{gain:.2f}×"},
                {
                    "label": "Phase relation",
                    "value": "inverted (≈180°)" if inverted else "in phase (≈0°)",
                },
                {
                    "label": "Window",
                    "value": (
                        "0 – "
                        f"{plotting.format_si(result.tran_stop or result.tran[-1].time, 's')}"
                    ),
                },
            ]
        )
        plot_svg = plotting.transient_svg(result.tran)
        plot_caption = (
            "Input and output waveforms from the ngspice .tran run. "
            "Vin is the source node; Vout is the node across RL."
        )

    return {
        "analysis": result.analysis,
        "analysis_label": spice_engine.ANALYSIS_LABELS[result.analysis],
        "spice_rows": spice_rows,
        "analytical_rows": analytical_rows,
        "delta_rows": delta_rows,
        "spice_region": spice_region,
        "analytical_region": analytical_region,
        "analytical_note": analytical_note,
        "metrics": metrics,
        "plot_svg": plot_svg,
        "plot_caption": plot_caption,
        "source_text": source_text,
        "warnings": list(result.warnings),
        "netlist": result.netlist,
        "log": result.log,
        "engine": result.engine,
        "model": result.model,
        "sweep_start": result.sweep_start,
        "sweep_stop": result.sweep_stop,
        "tran_stop": result.tran_stop,
    }


def create_app() -> Flask:
    app = Flask(__name__)

    def render(
        mode: str,
        values,
        units,
        errors=None,
        form_error=None,
        result=None,
    ):
        return render_template(
            "index.html",
            mode=mode,
            mode_label=model.MODE_LABELS[mode],
            mode_choices=MODE_CHOICES,
            values=values,
            units=units,
            unit_choices=UNIT_CHOICES,
            errors=errors or {},
            form_error=form_error,
            result=result,
            acceptance=ACCEPTANCE_CASES,
        )

    def render_simulator(
        analysis: str,
        values,
        units,
        errors=None,
        form_error=None,
        result=None,
        run_error=None,
        engine_ready: bool = True,
        engine_label: str = "",
        engine_detail=None,
    ):
        return render_template(
            "simulator.html",
            analysis=analysis,
            analysis_label=spice_validation.ANALYSIS_LABELS.get(analysis, analysis),
            analysis_choices=spice_validation.ANALYSIS_CHOICES,
            values=values,
            units=units,
            unit_choices=SPICE_UNIT_CHOICES,
            errors=errors or {},
            form_error=form_error,
            result=result,
            run_error=run_error,
            engine_ready=engine_ready,
            engine_label=engine_label,
            engine_detail=engine_detail,
            model_name=spice_engine.MODEL_NAME,
            reference_beta=SPICE_REFERENCE_BETA,
            reference_vbe=SPICE_REFERENCE_VBE,
        )

    @app.get("/simulator")
    def simulator_get():
        analysis, error = spice_validation.parse_analysis(
            request.args.get("analysis")
        )
        if error is not None:
            analysis = spice_engine.ANALYSIS_DC
        values = dict(SPICE_DEFAULT_FORM, analysis=analysis)
        ready, label, detail = spice_engine.engine_status()
        return render_simulator(
            analysis,
            values,
            dict(SPICE_DEFAULT_UNITS),
            form_error=error.message if error else None,
            engine_ready=ready,
            engine_label=label,
            engine_detail=detail,
        )

    @app.post("/simulator")
    def simulator_post():
        analysis, analysis_error = spice_validation.parse_analysis(
            request.form.get("analysis")
        )
        units = _selected_units(
            request.form, SPICE_DEFAULT_UNITS, SPICE_UNIT_CHOICES
        )
        render_analysis = analysis or spice_engine.ANALYSIS_DC
        ready, label, detail = spice_engine.engine_status()

        if analysis_error is not None:
            return render_simulator(
                render_analysis,
                request.form,
                units,
                form_error=analysis_error.message,
                engine_ready=ready,
                engine_label=label,
                engine_detail=detail,
            )

        base_values = _to_base_units(
            request.form,
            units,
            spice_validation.SPICE_FIELDS,
            SPICE_UNIT_CHOICES,
        )
        inputs, errors = spice_validation.parse_spice_inputs(base_values)

        if errors:
            return render_simulator(
                render_analysis,
                request.form,
                units,
                errors={error.field: error.message for error in errors},
                engine_ready=ready,
                engine_label=label,
                engine_detail=detail,
            )

        try:
            result = spice_engine.run(inputs, analysis)
            view = _build_simulator_view(result, inputs)
        except spice_engine.SpiceError as exc:
            return render_simulator(
                render_analysis,
                request.form,
                units,
                run_error=str(exc),
                engine_ready=ready,
                engine_label=label,
                engine_detail=detail,
            )
        except (ValueError, ZeroDivisionError, OverflowError):
            return render_simulator(
                render_analysis,
                request.form,
                units,
                run_error=(
                    "The simulation finished, but the result could not be "
                    "processed safely."
                ),
                engine_ready=ready,
                engine_label=label,
                engine_detail=detail,
            )

        return render_simulator(
            render_analysis,
            request.form,
            units,
            result=view,
            engine_ready=True,
            engine_label=result.engine,
            engine_detail=None,
        )

    @app.get("/")
    def index_get():
        mode, error = validation.parse_mode(request.args.get("mode"))
        if error is not None:
            mode = model.MODE_DIVIDER
        values = dict(DEFAULT_FORM, mode=mode)
        return render(
            mode,
            values,
            dict(DEFAULT_UNITS),
            form_error=error.message if error else None,
        )

    @app.post("/")
    def index_post():
        mode, mode_error = validation.parse_mode(request.form.get("mode"))
        units = _selected_units(request.form)
        render_mode = mode or model.MODE_DIVIDER

        if mode_error is not None:
            return render(
                render_mode,
                request.form,
                units,
                form_error=mode_error.message,
            )

        fields = validation.MODE_FIELDS[mode]
        inputs, errors = validation.parse_inputs_for_mode(
            _to_base_units(request.form, units, fields),
            mode,
        )

        if errors:
            return render(
                render_mode,
                request.form,
                units,
                errors={error.field: error.message for error in errors},
            )

        try:
            evaluation = evaluate.evaluate(inputs, mode)
            result = _build_view(evaluation)
        except (ValueError, ZeroDivisionError, OverflowError):
            return render(
                render_mode,
                request.form,
                units,
                form_error="Inputs are outside the numerically stable range.",
            )

        return render(render_mode, request.form, units, result=result)

    return app


app = create_app()
