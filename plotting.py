"""Dependency-free SVG plots for the Lab 04 simulator.

The plots are deliberately plain: axes, ticks, labels, a legend and one
polyline per real data series.  Every point comes from a parsed ngspice output
file, so the browser never draws a hard-coded trace.
"""

from __future__ import annotations

import html
import math
from collections.abc import Sequence

from spice_engine import AcPoint, TranPoint

INK = "#17212b"
MUTED = "#5d6b7a"
GRID = "#d7dee6"
MAG = "#1f5f8b"
PHASE = "#b45f06"
VIN = "#1d6b45"
VOUT = "#a33a1f"

PREFIXES = (
    (1e9, "G"),
    (1e6, "M"),
    (1e3, "k"),
    (1.0, ""),
    (1e-3, "m"),
    (1e-6, "µ"),
    (1e-9, "n"),
    (1e-12, "p"),
)


def format_si(value: float, unit: str = "") -> str:
    """Format a number with an engineering prefix, e.g. 1000 -> '1 k'."""
    if value == 0:
        return f"0 {unit}".strip()
    for scale, prefix in PREFIXES:
        if abs(value) >= scale:
            number = value / scale
            text = f"{number:.3g}"
            return f"{text} {prefix}{unit}".strip()
    text = f"{value:.3g}"
    return f"{text} {unit}".strip()


def _escape(text: str) -> str:
    return html.escape(str(text), quote=True)


def _nice_ticks(low: float, high: float, count: int = 5) -> list[float]:
    if not (math.isfinite(low) and math.isfinite(high)):
        return [0.0, 1.0]
    if high <= low:
        high = low + 1.0
    span = high - low
    raw_step = span / max(count - 1, 1)
    exponent = math.floor(math.log10(raw_step))
    magnitude = 10.0 ** exponent
    candidates = [1.0, 2.0, 2.5, 5.0, 10.0]
    step = min(candidates, key=lambda value: abs(value * magnitude - raw_step)) * magnitude
    start = math.ceil(low / step) * step
    end = math.floor(high / step) * step
    ticks = []
    value = start
    while value <= end + step * 0.001 and len(ticks) < 12:
        ticks.append(round(value, 12))
        value += step
    return ticks or [low, high]


def _log_ticks(low: float, high: float) -> list[float]:
    start = math.floor(math.log10(low))
    stop = math.ceil(math.log10(high))
    ticks = []
    for exponent in range(start, stop + 1):
        ticks.append(10.0 ** exponent)
    return ticks


def _unwrap_phase(points: Sequence[AcPoint]) -> list[float]:
    phases: list[float] = []
    previous: float | None = None
    for point in points:
        phase = point.phase_deg
        if previous is not None:
            while phase - previous > 180.0:
                phase -= 360.0
            while phase - previous < -180.0:
                phase += 360.0
        phases.append(phase)
        previous = phase
    return phases


def _axis_line(x1, y1, x2, y2) -> str:
    return (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        f'stroke="{INK}" stroke-width="1"/>'
    )


def _grid_line(x1, y1, x2, y2) -> str:
    return (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        f'stroke="{GRID}" stroke-width="1"/>'
    )


def _text(x, y, text, *, anchor="start", size=11, color=MUTED, weight="normal") -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
        f'font-size="{size}" font-weight="{weight}" fill="{color}">'
        f"{_escape(text)}</text>"
    )


def bode_svg(ac_points: Sequence[AcPoint], width: int = 760, height: int = 440) -> str:
    points = tuple(ac_points)
    if len(points) < 2:
        raise ValueError("bode_svg needs at least two AC points")

    left, right, top = 74.0, 24.0, 34.0
    plot_width = width - left - right
    mag_top, mag_height = top, 168.0
    phase_top, phase_height = 252.0, 148.0

    frequencies = [point.frequency for point in points]
    f_min, f_max = min(frequencies), max(frequencies)
    if f_min <= 0:
        f_min = 1.0
    log_min, log_max = math.log10(f_min), math.log10(f_max)
    if log_max <= log_min:
        log_max = log_min + 1.0

    def x_for(frequency: float) -> float:
        ratio = (math.log10(max(frequency, f_min)) - log_min) / (log_max - log_min)
        return left + ratio * plot_width

    gains = [point.gain_db for point in points]
    gain_low, gain_high = min(gains), max(gains)
    gain_pad = max((gain_high - gain_low) * 0.12, 1.0)
    gain_ticks = _nice_ticks(gain_low - gain_pad, gain_high + gain_pad, 5)
    gain_low, gain_high = gain_ticks[0], gain_ticks[-1]
    if gain_high <= gain_low:
        gain_high = gain_low + 1.0

    phases = _unwrap_phase(points)
    phase_low, phase_high = min(phases), max(phases)
    phase_pad = max((phase_high - phase_low) * 0.12, 5.0)
    phase_ticks = _nice_ticks(phase_low - phase_pad, phase_high + phase_pad, 4)
    phase_low, phase_high = phase_ticks[0], phase_ticks[-1]
    if phase_high <= phase_low:
        phase_high = phase_low + 1.0

    def y_mag(value: float) -> float:
        ratio = (gain_high - value) / (gain_high - gain_low)
        return mag_top + ratio * mag_height

    def y_phase(value: float) -> float:
        ratio = (phase_high - value) / (phase_high - phase_low)
        return phase_top + ratio * phase_height

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'role="img" aria-label="AC Bode plot" class="plot-svg">',
        "<title>AC Bode plot from ngspice</title>",
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#ffffff"/>',
    ]

    for tick in _log_ticks(f_min, f_max):
        if f_min <= tick <= f_max:
            x = x_for(tick)
            parts.append(_grid_line(x, mag_top, x, mag_top + mag_height))
            parts.append(_grid_line(x, phase_top, x, phase_top + phase_height))

    for tick in gain_ticks:
        y = y_mag(tick)
        parts.append(_grid_line(left, y, left + plot_width, y))
        parts.append(_text(left - 8, y + 4, f"{tick:.3g}", anchor="end", size=10))
    for tick in phase_ticks:
        y = y_phase(tick)
        parts.append(_grid_line(left, y, left + plot_width, y))
        parts.append(_text(left - 8, y + 4, f"{tick:.3g}", anchor="end", size=10))

    parts.extend(
        [
            _axis_line(left, mag_top, left, mag_top + mag_height),
            _axis_line(left, mag_top + mag_height, left + plot_width, mag_top + mag_height),
            _axis_line(left, phase_top, left, phase_top + phase_height),
            _axis_line(left, phase_top + phase_height, left + plot_width, phase_top + phase_height),
        ]
    )

    mag_points = " ".join(
        f"{x_for(point.frequency):.1f},{y_mag(point.gain_db):.1f}" for point in points
    )
    phase_points = " ".join(
        f"{x_for(point.frequency):.1f},{y_phase(phase):.1f}"
        for point, phase in zip(points, phases)
    )
    parts.extend(
        [
            f'<polyline points="{mag_points}" fill="none" stroke="{MAG}" '
            'stroke-width="2" stroke-linejoin="round"/>',
            f'<polyline points="{phase_points}" fill="none" stroke="{PHASE}" '
            'stroke-width="2" stroke-linejoin="round"/>',
        ]
    )

    for tick in _log_ticks(f_min, f_max):
        if f_min <= tick <= f_max:
            parts.append(
                _text(
                    x_for(tick),
                    phase_top + phase_height + 18,
                    format_si(tick, "Hz"),
                    anchor="middle",
                    size=10,
                )
            )

    parts.extend(
        [
            _text(left, mag_top - 10, "Gain magnitude  |Vout/Vin|", size=12, color=INK, weight="bold"),
            _text(left, phase_top - 10, "Phase  ∠Vout − ∠Vin", size=12, color=INK, weight="bold"),
            _text(left + plot_width / 2, height - 10, "Frequency (Hz)", anchor="middle", size=12, color=INK),
            _text(14, mag_top + mag_height / 2, "Gain (dB)", anchor="middle", size=11),
            _text(14, phase_top + phase_height / 2, "Phase (deg)", anchor="middle", size=11),
        ]
    )
    parts.append("</svg>")
    return "\n".join(parts)


def transient_svg(points: Sequence[TranPoint], width: int = 760, height: int = 340) -> str:
    rows = tuple(points)
    if len(rows) < 2:
        raise ValueError("transient_svg needs at least two time points")

    left, right, top, bottom = 74.0, 24.0, 36.0, 52.0
    plot_width = width - left - right
    plot_height = height - top - bottom

    t_max = max(row.time for row in rows)
    if t_max <= 0:
        t_max = 1.0
    if t_max >= 1e-3:
        time_scale, time_unit = 1e3, "ms"
    elif t_max >= 1e-6:
        time_scale, time_unit = 1e6, "µs"
    else:
        time_scale, time_unit = 1.0, "s"

    v_max = max(max(abs(row.vin), abs(row.vout)) for row in rows)
    if v_max < 1.0:
        volt_scale, volt_unit = 1e3, "mV"
    else:
        volt_scale, volt_unit = 1.0, "V"
    v_limit = max(v_max * 1.1, 1e-9)
    volt_ticks = _nice_ticks(-v_limit, v_limit, 5)
    v_low, v_high = volt_ticks[0], volt_ticks[-1]
    if v_high <= v_low:
        v_high = v_low + 1.0

    def x_for(time: float) -> float:
        return left + (time / t_max) * plot_width

    def y_for(voltage: float) -> float:
        ratio = (v_high - voltage) / (v_high - v_low)
        return top + ratio * plot_height

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'role="img" aria-label="Transient waveform" class="plot-svg">',
        "<title>Transient waveform from ngspice</title>",
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#ffffff"/>',
    ]

    for tick in volt_ticks:
        y = y_for(tick)
        parts.append(_grid_line(left, y, left + plot_width, y))
        label = f"{tick * volt_scale:.3g}"
        parts.append(_text(left - 8, y + 4, label, anchor="end", size=10))

    time_ticks = _nice_ticks(0.0, t_max, 5)
    for tick in time_ticks:
        x = x_for(tick)
        parts.append(_grid_line(x, top, x, top + plot_height))
        parts.append(
            _text(x, top + plot_height + 18, f"{tick * time_scale:.3g}", anchor="middle", size=10)
        )

    parts.extend(
        [
            _axis_line(left, top, left, top + plot_height),
            _axis_line(left, top + plot_height, left + plot_width, top + plot_height),
        ]
    )

    vin_points = " ".join(
        f"{x_for(row.time):.1f},{y_for(row.vin):.1f}" for row in rows
    )
    vout_points = " ".join(
        f"{x_for(row.time):.1f},{y_for(row.vout):.1f}" for row in rows
    )
    parts.extend(
        [
            f'<polyline points="{vin_points}" fill="none" stroke="{VIN}" '
            'stroke-width="1.8" stroke-linejoin="round"/>',
            f'<polyline points="{vout_points}" fill="none" stroke="{VOUT}" '
            'stroke-width="1.8" stroke-linejoin="round"/>',
            f'<line x1="{left + 10}" y1="{top + 14}" x2="{left + 34}" y2="{top + 14}" '
            f'stroke="{VIN}" stroke-width="3"/>',
            _text(left + 40, top + 18, "Vin", size=11, color=INK),
            f'<line x1="{left + 90}" y1="{top + 14}" x2="{left + 114}" y2="{top + 14}" '
            f'stroke="{VOUT}" stroke-width="3"/>',
            _text(left + 120, top + 18, "Vout", size=11, color=INK),
            _text(left + plot_width / 2, height - 10, f"Time ({time_unit})", anchor="middle", size=12, color=INK),
            _text(14, top + plot_height / 2, f"Voltage ({volt_unit})", anchor="middle", size=11),
        ]
    )
    parts.append("</svg>")
    return "\n".join(parts)
