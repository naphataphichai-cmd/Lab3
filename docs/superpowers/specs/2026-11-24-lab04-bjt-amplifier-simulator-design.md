# Lab 04 — BJT CE Amplifier Simulator v1 — Design

## Intent

Extend the existing ENG29 2121 Lab 03 Flask app into a working Common-Emitter
(CE) amplifier simulator for one reference voltage-divider circuit. The Lab 03
analytical DC bias calculator (Fixed / Emitter / Divider) stays intact. The new
work adds real ngspice runs for DC operating point, AC frequency response and
transient waveforms, with plots, units, provenance and explicit error states.

Why: the Lab 04 handout requires a simulation-backed result, not a mock plot.
The browser must show data that came from ngspice, and the Lab 03 analytical
result must remain available as an independent, clearly labelled reference.

## Goals

- Preserve all three Lab 03 bias modes, their validation and their 113 tests.
- Run real ngspice 47 for one CE voltage-divider reference circuit:
  - `.op` → `VB, VE, VC, VCE, IC, IB, IE`
  - `.ac` → frequency, gain magnitude (dB), phase (degrees)
  - `.tran` → time, `Vin`, `Vout`
- Expose VCC, R1, R2, RC, RE, RL, Cin, Cout, source amplitude and frequency with
  explicit units.
- Show engine version, BJT model name, run status, netlist and run log.
- Separate SPICE results from the Lab 03 analytical reference, including the
  assumptions behind the analytical numbers.
- Keep the app usable on desktop and phone widths.
- Record B1–B8 browser acceptance and a reproducible README setup.

## Non-goals

- Drag-and-drop schematic editing, arbitrary circuits, netlist import.
- AC or transient analysis for the Fixed and Emitter bias modes.
- FETs, small-signal hand analysis, transient animation, deployment.
- A Python SPICE solver; ngspice is the simulation engine.
- Changing the Lab 03 numerical formulas or its result table.

## Constraints

- Windows environment; ngspice is an external executable, not a pip package.
- No new Python dependency for charts: plots are server-rendered SVG from the
  parsed ngspice data, so the page works offline and is easy to test.
- `subprocess.run` must use an argument list, `shell=False`, a timeout and a
  per-run temporary working directory.
- No fabricated traces, hard-coded success values or hidden ngspice errors.
- The Lab 03 routes and templates must keep working unchanged.

## Approaches considered

1. **Separate `/simulator` page with server-rendered SVG (chosen).**
   Low regression risk: Lab 03 stays byte-for-byte in behaviour, while the
   simulator gets its own form, results and error states. SVG keeps the
   dependency list at Flask + pytest and makes the real-data provenance easy to
   inspect.
2. **Extend the single Lab 03 page with tabs and a JS chart library.**
   Closer to the handout wireframe, but mixes the two result models, adds a
   CDN/runtime dependency and raises the risk of breaking the Lab 03 route
   tests. Rejected for this first version.
3. **Create a new Flask project.**
   Contradicts the handout's "extend, do not recreate" rule and loses the Lab 03
   regression evidence. Rejected.

## Architecture

```text
app.py                     Flask routes: Lab 03 index + Lab 04 /simulator
engineering/               Unchanged Lab 03 analytical DC model (reference)
spice_engine.py            Netlist, subprocess, parsing, provenance
spice_validation.py        SPICE input ranges + analysis selection
plotting.py                Dependency-free SVG for Bode and transient plots
templates/simulator.html   Lab 04 page
static/style.css           Shared lab-sheet styles + simulator layout
tests/                     Lab 03 tests + Lab 04 unit/route/integration tests
docs/validation.md         Lab 03 A1–A5 + Lab 04 B1–B8 record
```

The adapter exposes:

```python
SpiceInputs(vcc, r1, r2, rc, re, rl, cin, cout, amplitude, frequency)
build_netlist(inputs, analysis) -> str
run(inputs, analysis, *, ngspice_path=None, timeout=20.0) -> SpiceResult
SpiceResult(analysis, inputs, model, engine, netlist, log, op, ac, tran, ...)
SpiceError(message)
```

`find_ngspice()` checks `NGSPICE_BIN`, then
`tools/ngspice/Spice64/bin/ngspice_con.exe`, then `ngspice_con` / `ngspice` on
`PATH`. The local `tools/` download is gitignored; the README documents the
download and extraction steps.

## Reference circuit and model

One CE voltage-divider stage, as specified by the handout:

- `VCC` → `R1` → base; base → `R2` → ground.
- `RC` from `VCC` to collector; `RE` from emitter to ground.
- `Q1` NPN, collector/base/emitter.
- `Cin` couples the source to the base; `Cout` couples the collector to `RL`.
- Source: DC 0, AC 1 V for `.ac`, SIN(0, amplitude, frequency) for `.tran`.

BJT model: standard Motorola 2N3904 Gummel-Poon card (the common
`IS=6.734f ... BF=416.4 ...` model). The model name and full card are shown in
the UI and recorded in `docs/validation.md`. The analytical reference uses the
Lab 03 assumptions (`β = 100`, `VBE = 0.70 V`), so the two DC results are
expected to differ; the UI says so.

## Analysis definitions

- **DC** — coupling capacitors are open. Report `VB, VE, VC, VCE, IC, IB, IE`
  from the `.op` output. `IE` is `IC + IB`; `VCE` is `VC − VE` from the same
  run. Warn when `VCE ≤ 0.2 V` (saturation) or `IC ≤ 0` (cutoff).
- **AC** — fixed sweep 0.1 Hz–100 MHz, 20 points/decade. `Vin` is the source node `in` (AC 1 V, 0°); `Vout` is the
  node `out` across `RL`. Gain is `20·log10(|Vout|/|Vin|)`; phase is
  `arg(Vout) − arg(Vin)` in degrees. If the −3 dB crossings are outside the
  sweep, the UI says "not determined in sweep range" instead of inventing a
  number.
- **Transient** — stop time is 5 source cycles, clamped to 10 µs–50 ms; step is
  `stop/2000`. Plot `Vin` and `Vout` against time. Report peak-to-peak values
  over the last 80 % of the window and whether the output is inverted.

## Error handling

`SpiceError` covers: engine missing, timeout, non-zero exit, missing/empty
result file, unparsable result, non-finite values. The route renders an error
banner and never shows a previous run's plots as the current result. Validation
errors stay next to the field, matching Lab 03. All user input is parsed to
finite floats and re-formatted by the adapter; raw form text never reaches the
netlist or the command line.

## UI

- Lab 03 page gains one link to `/simulator`; everything else is unchanged.
- Simulator page: left = circuit + parameters, centre = analysis choice + plot,
  right = SPICE results + Lab 03 reference + engine status.
- Analysis is chosen with radio tabs (DC / AC / Transient) and applied by the
  single "Run simulation" button.
- Netlist and log are in collapsible `<details>` blocks for provenance.
- Responsive at 980 px and 700 px; tables scroll horizontally on phones.

## Verification

- Unit tests: netlist contents, parsers (fixtures), validation ranges, SVG
  output, route success/error paths with a fake engine.
- Integration tests: real ngspice runs for DC/AC/tran, skipped when the engine
  is absent.
- Browser acceptance B1–B8 against the running Flask app; record expected,
  observed, units, status and evidence in `docs/validation.md`.
- Regression: the full Lab 03 suite must still pass.

## Calls made for this implementation

- Continue in the existing Lab3 repository rather than creating a new project.
- Install ngspice 47 locally under `tools/` for this machine; do not commit the
  binary.
- Use the standard 2N3904 model because no instructor starter kit was present.
- Use server-rendered SVG instead of a JavaScript chart library.
- Keep the simulator on its own page to protect the Lab 03 regression suite.
