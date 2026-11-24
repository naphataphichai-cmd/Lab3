# Lab 04 BJT CE Amplifier Simulator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Extend the Lab 03 Flask DC-bias app with real ngspice DC, AC and transient simulation for one CE voltage-divider amplifier, plots, provenance and browser acceptance evidence.

**Architecture:** Keep `engineering/` and the Lab 03 index untouched. Add `spice_engine.py` (netlist → subprocess → parse), `spice_validation.py` (ranges), `plotting.py` (SVG), and a separate `/simulator` page. ngspice 47 is a local external executable detected at `tools/ngspice/Spice64/bin/ngspice_con.exe` or `NGSPICE_BIN`.

**Tech Stack:** Python 3.12, Flask 3, pytest 8, ngspice 47, server-rendered SVG. No new Python dependencies.

**Spec:** `docs/superpowers/specs/2026-11-24-lab04-bjt-amplifier-simulator-design.md`

## Global Constraints

- Preserve all Lab 03 routes, formulas and 113 tests.
- `subprocess.run([...], shell=False, timeout=...)`; one temporary working directory per run.
- No fabricated plots or success values; every plot point comes from a real ngspice output file.
- All inputs become finite floats before netlist generation; raw form text never reaches the command line.
- SPICE results and the Lab 03 analytical reference are labelled separately.
- The 2N3904 model card and ngspice version are visible in the UI and recorded in `docs/validation.md`.

## Review Focus

- ngspice missing / not on PATH → clear error, no stale success panel.
- Timeout or non-zero exit → error banner, no old plot.
- Empty or truncated `ac.txt` / `tran.txt` → parse error, not a blank chart.
- `RE = 0`, negative amplitude, zero frequency, non-finite values → field error before netlist generation.
- Very low/high source frequency → transient window clamped; AC sweep stays valid; UI says when −3 dB is not found.

---

### Task 1: ngspice adapter and DC operating point

**Files:**
- Create: `spice_engine.py`
- Test: `tests/test_spice_engine.py`

**Interfaces:**
- Produces: `SpiceInputs`, `SpiceResult`, `SpiceError`, `find_ngspice()`, `build_netlist(inputs, analysis)`, `run(inputs, analysis, *, ngspice_path=None, timeout=20.0)`.

- [x] Write failing tests for `find_ngspice`, netlist contents and a real DC run.
- [x] Run tests; confirm import/attribute failures.
- [x] Implement the adapter with `ANALYSIS_DC/AC/TRAN`, the 2N3904 card, `.control` blocks, `wrdata`, parsing and error paths.
- [x] Run the DC integration test; confirm `VB/VE/VC/VCE/IC/IB/IE` are finite and `IC > 0`.
- [x] Commit.

### Task 2: AC and transient parsing

**Files:**
- Modify: `spice_engine.py`
- Test: `tests/test_spice_engine.py`

**Interfaces:**
- Produces: `AcPoint(frequency, gain_db, phase_deg, gain_mag)`, `TranPoint(time, vin, vout)`, `parse_ac_table(text)`, `parse_tran_table(text)`.

- [x] Write failing tests with small fixture tables and real `.ac` / `.tran` runs.
- [x] Run tests; confirm failure.
- [x] Implement parsing: frequency/real/imag columns for AC; time/vin/vout for transient; reject empty or non-finite data.
- [x] Run tests; confirm AC has >50 points and transient has >100 points.
- [x] Commit.

### Task 3: SPICE input validation and units

**Files:**
- Create: `spice_validation.py`
- Modify: `app.py` (unit tables only)
- Test: `tests/test_spice_validation.py`

**Interfaces:**
- Produces: `ANALYSES`, `parse_analysis(raw)`, `parse_spice_inputs(form)`, `SPICE_FIELDS`.
- Consumes: `spice_engine.SpiceInputs`.

- [x] Write failing tests for accepted baseline values, `RE=0`, negative amplitude, zero frequency, unknown analysis and missing fields.
- [x] Run tests; confirm failure.
- [x] Implement the range checks and `FieldError` messages; extend `UNIT_SCALE`/`UNIT_CHOICES` with pF/nF/µF/F/Hz/kHz/MHz.
- [x] Run tests; confirm pass.
- [x] Commit.

### Task 4: SVG plots

**Files:**
- Create: `plotting.py`
- Test: `tests/test_plotting.py`

**Interfaces:**
- Produces: `bode_svg(ac_points, width=760, height=360) -> str`, `transient_svg(tran_points, width=760, height=320) -> str`, `format_si(value, unit)`.

- [x] Write failing tests for axis labels, units, legend text and a polyline with one point per input.
- [x] Run tests; confirm failure.
- [x] Implement log-frequency Bode (magnitude and phase) and linear-time transient SVG with grid, ticks and escaped text.
- [x] Run tests; confirm pass.
- [x] Commit.

### Task 5: Simulator route and view model

**Files:**
- Modify: `app.py`
- Test: `tests/test_simulator_routes.py`

**Interfaces:**
- Produces: `GET /simulator`, `POST /simulator`, `build_simulator_view(result, inputs)`.
- Consumes: `spice_engine`, `spice_validation`, `plotting`, `engineering.evaluate`.

- [x] Write failing tests for GET defaults, successful DC POST with a fake engine, validation error, engine error and no stale result.
- [x] Run tests; confirm failure.
- [x] Implement the routes, unit conversion, analytical reference (`β=100`, `VBE=0.70 V`) and view model.
- [x] Run tests; confirm pass.
- [x] Commit.

### Task 6: Simulator template and CSS

**Files:**
- Create: `templates/simulator.html`
- Modify: `templates/base.html`, `templates/index.html`, `static/style.css`
- Test: `tests/test_simulator_routes.py`

**Interfaces:**
- Consumes: the view model from Task 5.

- [x] Add a failing route test that checks for the analysis tabs, run button, engine label, netlist `<details>` and the Lab 03 link.
- [x] Implement the page: circuit/parameters, analysis tabs, plots, SPICE results, analytical reference, engine status, netlist/log, error banner.
- [x] Add responsive styles; verify the Lab 03 page still renders.
- [x] Run tests; confirm pass.
- [x] Commit.

### Task 7: README, validation record and regression

**Files:**
- Modify: `README.md`, `docs/validation.md`
- Test: full suite

- [x] Document ngspice installation, `NGSPICE_BIN`, model, analyses, measurement references and limitations.
- [x] Run `pytest -q`; confirm all Lab 03 + Lab 04 tests pass.
- [x] Start Flask and run B1–B8 with the browser tool; record expected/observed/status/evidence in `docs/validation.md`.
- [x] Capture desktop/mobile evidence where the browser window permits; mark anything not run honestly.
- [x] Commit.

### Task 8: Final verification and handoff

**Files:**
- Modify: `README.md` (commit SHA), `docs/validation.md` (final status)

- [x] Run `pytest -q`, `git diff --check`, `git status`.
- [x] Confirm no `.venv/`, `tools/` binaries, temp `.raw` or logs are staged.
- [x] Commit the Lab 04 work; report the local commit SHA and the push command for approval.
