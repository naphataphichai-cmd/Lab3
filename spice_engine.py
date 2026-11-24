"""ngspice adapter for the Lab 04 common-emitter amplifier simulator.

The module owns everything that touches the external simulator: netlist
generation, the subprocess call, the ASCII result files and the parser.  The
Flask layer only passes validated floats in and receives a ``SpiceResult`` out.
"""

from __future__ import annotations

import math
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from engineering import model as bias_model

ANALYSIS_DC = "dc"
ANALYSIS_AC = "ac"
ANALYSIS_TRAN = "tran"
ANALYSES = (ANALYSIS_DC, ANALYSIS_AC, ANALYSIS_TRAN)

MODE_DIVIDER = bias_model.MODE_DIVIDER
MODE_FIXED = bias_model.MODE_FIXED
MODE_EMITTER = bias_model.MODE_EMITTER
MODES = bias_model.MODES
MODE_LABELS = bias_model.MODE_LABELS

ANALYSIS_LABELS = {
    ANALYSIS_DC: "DC operating point (.op)",
    ANALYSIS_AC: "AC frequency response (.ac)",
    ANALYSIS_TRAN: "Transient waveform (.tran)",
}

MODEL_NAME = "2N3904"
# Standard Motorola 2N3904 Gummel-Poon model, as used by the common ngspice
# examples and vendor model libraries.  The exact card is shown in the UI so a
# reader can reproduce the run.
MODEL_CARD = (
    "NPN(IS=6.734f XTI=3 EG=1.11 VAF=74.03 BF=416.4 NE=1.259 ISE=6.734f "
    "IKF=66.78m XTB=1.5 BR=.7371 NC=2 ISC=0 IKR=0 RC=1 CJC=3.638p MJC=.3085 "
    "VJC=.75 FC=.5 CJE=4.493p MJE=.2593 VJE=.75 TR=239.5n TF=301.2p ITF=.4 "
    "VTF=4 XTF=2 RB=10)"
)

DEFAULT_TIMEOUT = 20.0
AC_POINTS_PER_DECADE = 20
# Wide enough to show both coupling and device cutoffs of the reference stage.
AC_MIN_HZ = 0.1
AC_MAX_HZ = 100e6
TRAN_MIN_SECONDS = 10e-6
TRAN_MAX_SECONDS = 50e-3
TRAN_POINTS = 2000


class SpiceError(Exception):
    """A user-facing simulation failure (missing engine, timeout, bad output)."""


@dataclass(frozen=True)
class SpiceInputs:
    vcc: float
    rc: float
    rl: float
    cin: float
    cout: float
    amplitude: float
    frequency: float
    mode: str = MODE_DIVIDER
    r1: float | None = None
    r2: float | None = None
    rb: float | None = None
    re: float | None = None


@dataclass(frozen=True)
class OperatingPoint:
    vb: float
    ve: float
    vc: float
    vce: float
    ic: float
    ib: float
    ie: float


@dataclass(frozen=True)
class AcPoint:
    frequency: float
    gain_mag: float
    gain_db: float
    phase_deg: float


@dataclass(frozen=True)
class TranPoint:
    time: float
    vin: float
    vout: float


@dataclass(frozen=True)
class SpiceResult:
    analysis: str
    inputs: SpiceInputs
    model: str
    engine: str
    netlist: str
    log: str
    op: OperatingPoint | None = None
    ac: tuple[AcPoint, ...] = ()
    tran: tuple[TranPoint, ...] = ()
    sweep_start: float | None = None
    sweep_stop: float | None = None
    tran_stop: float | None = None
    warnings: tuple[str, ...] = ()


def _num(value: float) -> str:
    if not math.isfinite(value):
        raise SpiceError("The netlist contains a non-finite value.")
    if value == 0:
        return "0"
    return f"{value:.12g}"


def _local_candidates() -> list[Path]:
    root = Path(__file__).resolve().parent
    base = root / "tools" / "ngspice" / "Spice64" / "bin"
    return [base / "ngspice_con.exe", base / "ngspice.exe", base / "ngspice_con", base / "ngspice"]


def find_ngspice() -> str:
    """Return the ngspice executable path or raise a user-facing error."""
    env_path = os.environ.get("NGSPICE_BIN")
    if env_path:
        candidate = Path(env_path)
        if candidate.is_file():
            return str(candidate)
        raise SpiceError(
            "NGSPICE_BIN is set but does not point to an executable file: "
            f"{env_path}"
        )

    for candidate in _local_candidates():
        if candidate.is_file():
            return str(candidate)

    for name in ("ngspice_con", "ngspice"):
        found = shutil.which(name)
        if found:
            return found

    raise SpiceError(
        "ngspice was not found. Install ngspice and put it on PATH, or set "
        "NGSPICE_BIN to the executable. See README.md for the Windows steps."
    )


def ngspice_available() -> bool:
    try:
        find_ngspice()
    except SpiceError:
        return False
    return True


def engine_status() -> tuple[bool, str, str | None]:
    """Return (ready, label, detail) for the UI status strip."""
    try:
        executable = find_ngspice()
    except SpiceError as exc:
        return False, "ngspice not available", str(exc)
    return True, _engine_version(executable), executable


def _engine_version(executable: str) -> str:
    try:
        completed = subprocess.run(
            [executable, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            shell=False,
        )
    except (OSError, subprocess.SubprocessError):
        return "ngspice (version unknown)"

    match = re.search(r"ngspice-(\d+(?:\.\d+)?)", completed.stdout + completed.stderr)
    return f"ngspice-{match.group(1)}" if match else "ngspice (version unknown)"


def _ac_sweep(frequency: float) -> tuple[float, float]:
    return AC_MIN_HZ, AC_MAX_HZ


def _tran_window(frequency: float) -> tuple[float, float]:
    stop = min(max(5.0 / frequency, TRAN_MIN_SECONDS), TRAN_MAX_SECONDS)
    step = stop / TRAN_POINTS
    return step, stop


def build_netlist(inputs: SpiceInputs, analysis: str) -> str:
    """Build a batch netlist with a ``.control`` block for one analysis."""
    if analysis not in ANALYSES:
        raise SpiceError(f"Unknown analysis: {analysis}")

    mode = inputs.mode
    if mode not in MODES:
        raise SpiceError(f"Unknown circuit mode: {mode}")

    def _require(value: float | None, name: str) -> float:
        if value is None:
            raise SpiceError(f"{name} is required for this circuit mode.")
        return value

    lines = [
        f"* ENG29 2121 Lab 04 - CE {MODE_LABELS[mode]} amplifier (generated)",
        f"* mode: {mode}",
        f"* analysis: {analysis}",
        f"VCC vcc 0 DC {_num(inputs.vcc)}",
        (
            "VIN in 0 DC 0 AC 1 "
            f"SIN(0 {_num(inputs.amplitude)} {_num(inputs.frequency)})"
        ),
        f"RC vcc c {_num(inputs.rc)}",
        f"CIN in b {_num(inputs.cin)}",
        f"COUT c out {_num(inputs.cout)}",
        f"RL out 0 {_num(inputs.rl)}",
        f"Q1 c b e {MODEL_NAME}",
        f".model {MODEL_NAME} {MODEL_CARD}",
    ]

    if mode == MODE_DIVIDER:
        lines.extend(
            [
                f"R1 vcc b {_num(_require(inputs.r1, 'R1'))}",
                f"R2 b 0 {_num(_require(inputs.r2, 'R2'))}",
                f"RE e 0 {_num(_require(inputs.re, 'RE'))}",
            ]
        )
    elif mode == MODE_FIXED:
        lines.extend(
            [
                f"RB vcc b {_num(_require(inputs.rb, 'RB'))}",
                "VEMIT e 0 DC 0",
            ]
        )
    elif mode == MODE_EMITTER:
        lines.extend(
            [
                f"RB vcc b {_num(_require(inputs.rb, 'RB'))}",
                f"RE e 0 {_num(_require(inputs.re, 'RE'))}",
            ]
        )

    lines.append(".control")

    if analysis == ANALYSIS_DC:
        lines.extend(
            [
                "op",
                "print v(b) v(e) v(c) v(b)-v(e) @q1[ic] @q1[ib]",
            ]
        )
    elif analysis == ANALYSIS_AC:
        start, stop = _ac_sweep(inputs.frequency)
        lines.extend(
            [
                f"ac dec {AC_POINTS_PER_DECADE} {_num(start)} {_num(stop)}",
                "set wr_singlescale",
                "set wr_vecnames",
                "wrdata ac.txt v(out)",
            ]
        )
    else:
        step, stop = _tran_window(inputs.frequency)
        lines.extend(
            [
                f"tran {_num(step)} {_num(stop)}",
                "set wr_singlescale",
                "set wr_vecnames",
                "wrdata tran.txt v(in) v(out)",
            ]
        )

    lines.extend([".endc", ".end", ""])
    return "\n".join(lines)


_OP_PATTERN = re.compile(
    r"(?m)^\s*(v\(b\)|v\(e\)|v\(c\)|v\(b\)-v\(e\)|@q1\[ic\]|@q1\[ib\])"
    r"\s*=\s*([-+0-9.eE]+)\s*$"
)


def parse_op_log(log: str) -> OperatingPoint:
    values: dict[str, float] = {}
    for match in _OP_PATTERN.finditer(log):
        values[match.group(1)] = float(match.group(2))

    required = ("v(b)", "v(e)", "v(c)", "@q1[ic]", "@q1[ib]")
    if any(name not in values for name in required):
        raise SpiceError(
            "ngspice did not return a complete operating point. See the run log."
        )

    vb = values["v(b)"]
    ve = values["v(e)"]
    vc = values["v(c)"]
    ic = values["@q1[ic]"]
    ib = values["@q1[ib]"]
    numbers = (vb, ve, vc, ic, ib)
    if not all(math.isfinite(value) for value in numbers):
        raise SpiceError("ngspice returned a non-finite operating point.")

    return OperatingPoint(
        vb=vb,
        ve=ve,
        vc=vc,
        vce=vc - ve,
        ic=ic,
        ib=ib,
        ie=ic + ib,
    )


def _data_lines(text: str) -> list[list[float]]:
    rows: list[list[float]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            numbers = [float(part) for part in line.split()]
        except ValueError:
            # Header or a non-numeric line; the data rows are all numeric.
            continue
        rows.append(numbers)
    return rows


def parse_ac_table(text: str) -> tuple[AcPoint, ...]:
    points: list[AcPoint] = []
    for row in _data_lines(text):
        if len(row) < 3:
            continue
        frequency, real, imag = row[0], row[1], row[2]
        if not all(math.isfinite(value) for value in (frequency, real, imag)):
            raise SpiceError("ngspice returned a non-finite AC point.")
        if frequency <= 0:
            continue
        magnitude = math.hypot(real, imag)
        gain_db = 20.0 * math.log10(magnitude) if magnitude > 0 else -300.0
        phase_deg = math.degrees(math.atan2(imag, real))
        points.append(
            AcPoint(
                frequency=frequency,
                gain_mag=magnitude,
                gain_db=gain_db,
                phase_deg=phase_deg,
            )
        )

    if len(points) < 2:
        raise SpiceError("ngspice returned no usable AC data. See the run log.")
    return tuple(points)


def parse_tran_table(text: str) -> tuple[TranPoint, ...]:
    points: list[TranPoint] = []
    for row in _data_lines(text):
        if len(row) < 3:
            continue
        time, vin, vout = row[0], row[1], row[2]
        if not all(math.isfinite(value) for value in (time, vin, vout)):
            raise SpiceError("ngspice returned a non-finite transient point.")
        points.append(TranPoint(time=time, vin=vin, vout=vout))

    if len(points) < 2:
        raise SpiceError("ngspice returned no usable transient data. See the run log.")
    return tuple(points)


def _warnings_from_log(log: str) -> tuple[str, ...]:
    warnings = []
    for line in log.splitlines():
        text = line.strip()
        if text and re.search(r"\bwarning\b", text, re.IGNORECASE):
            warnings.append(text)
        if len(warnings) >= 5:
            break
    return tuple(warnings)


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise SpiceError(f"Could not read the ngspice output file: {exc}") from exc


def run(
    inputs: SpiceInputs,
    analysis: str,
    *,
    ngspice_path: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> SpiceResult:
    """Run one analysis and return parsed, provenance-carrying results."""
    if analysis not in ANALYSES:
        raise SpiceError(f"Unknown analysis: {analysis}")

    executable = ngspice_path or find_ngspice()
    if not Path(executable).is_file():
        raise SpiceError(f"ngspice executable not found: {executable}")

    netlist = build_netlist(inputs, analysis)
    engine = _engine_version(executable)

    with tempfile.TemporaryDirectory(prefix="lab04-ngspice-") as temp_dir:
        workdir = Path(temp_dir)
        circuit = workdir / "circuit.cir"
        log_path = workdir / "run.log"
        circuit.write_text(netlist, encoding="ascii")

        try:
            completed = subprocess.run(
                [executable, "-b", "-o", "run.log", "circuit.cir"],
                cwd=workdir,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise SpiceError(
                f"ngspice did not finish within {timeout:.0f} s. Try a simpler "
                "input or a longer timeout."
            ) from exc
        except OSError as exc:
            raise SpiceError(f"Could not start ngspice: {exc}") from exc

        log = _read_text(log_path) if log_path.exists() else (
            (completed.stdout or "") + (completed.stderr or "")
        )

        if completed.returncode != 0:
            tail = "\n".join(log.strip().splitlines()[-6:])
            raise SpiceError(
                f"ngspice exited with code {completed.returncode}. {tail}".strip()
            )

        fatal = re.search(r"(?im)^\s*(?:error|fatal)\b", log)
        if fatal:
            tail = "\n".join(log.strip().splitlines()[-6:])
            raise SpiceError(f"ngspice reported an error. {tail}".strip())

        warnings = list(_warnings_from_log(log))

        if analysis == ANALYSIS_DC:
            op = parse_op_log(log)
            if op.vce <= 0.2:
                warnings.append(
                    "The SPICE operating point is in saturation (VCE ≤ 0.2 V); "
                    "this point is not valid for amplifier use."
                )
            if op.ic <= 0:
                warnings.append(
                    "The SPICE operating point is in cutoff (IC ≤ 0)."
                )
            return SpiceResult(
                analysis=analysis,
                inputs=inputs,
                model=MODEL_NAME,
                engine=engine,
                netlist=netlist,
                log=log,
                op=op,
                warnings=tuple(warnings),
            )

        if analysis == ANALYSIS_AC:
            data_path = workdir / "ac.txt"
            if not data_path.is_file() or data_path.stat().st_size == 0:
                raise SpiceError(
                    "ngspice did not write ac.txt. See the run log for details."
                )
            points = parse_ac_table(_read_text(data_path))
            start, stop = _ac_sweep(inputs.frequency)
            return SpiceResult(
                analysis=analysis,
                inputs=inputs,
                model=MODEL_NAME,
                engine=engine,
                netlist=netlist,
                log=log,
                ac=points,
                sweep_start=start,
                sweep_stop=stop,
                warnings=tuple(warnings),
            )

        data_path = workdir / "tran.txt"
        if not data_path.is_file() or data_path.stat().st_size == 0:
            raise SpiceError(
                "ngspice did not write tran.txt. See the run log for details."
            )
        points = parse_tran_table(_read_text(data_path))
        _, stop = _tran_window(inputs.frequency)
        return SpiceResult(
            analysis=analysis,
            inputs=inputs,
            model=MODEL_NAME,
            engine=engine,
            netlist=netlist,
            log=log,
            tran=points,
            tran_stop=stop,
            warnings=tuple(warnings),
        )
