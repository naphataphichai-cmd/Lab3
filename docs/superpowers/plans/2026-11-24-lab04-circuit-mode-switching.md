# Lab 04 Circuit Mode Switching Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Voltage Divider, Fixed and Emitter bias mode switching to the Lab 04 `/simulator`, with real ngspice DC/AC/transient runs and matching Lab 03 analytical references.

**Architecture:** Keep one `/simulator` page. A server-rendered mode selector chooses the topology; `SpiceInputs.mode` drives netlist generation, validation field sets, the SVG schematic and the analytical reference. The existing divider behavior stays the default.

**Tech Stack:** Python 3.12, Flask 3, pytest 8, ngspice 47, server-rendered SVG, no new dependencies.

**Spec:** `docs/superpowers/specs/2026-11-24-lab04-circuit-mode-switching-design.md`

## Global Constraints

- Preserve Lab 03 routes, formulas, templates and all existing tests.
- Preserve the existing divider simulator defaults and results.
- Mode labels and mode strings come from `engineering.model`; do not invent new names.
- Emitter bias follows Lab 03: `RE` is unbypassed. Fixed bias ties the emitter to ground.
- Use real ngspice output only; no fabricated traces or success values.
- All form values become finite floats and are range-checked before netlist generation.
- Keep `subprocess.run([...], shell=False, timeout=...)` and one temporary directory per run.
- Fixed-bias emitter must have a DC path to ground; use `VEMIT e 0 DC 0`.
- Keep the page usable at desktop and phone widths.
- Record new browser acceptance cases after the existing B1–B8.

## Review Focus

- Fixed mode with a missing or zero `RB`: show a field error and do not run ngspice or show stale results.
- Fixed mode netlist: the emitter node must not float; a real `.op` must return `v(e) ≈ 0`.
- Emitter mode with a missing or zero `RE`: show a field error before netlist generation.
- Unknown `mode` in GET or POST: show a clear error, not a 500 or a silent divider fallback.
- Divider mode after adding `mode`: netlist, DC/AC/transient results and existing tests must be unchanged.
- Fixed-bias AC/transient can have much higher gain than the divider; plots must still render from real output, including any clipping.

---

### Task 1: Mode-aware `SpiceInputs` and netlist

**Files:**
- Modify: `spice_engine.py:56-67`, `spice_engine.py:196-250`
- Test: `tests/test_spice_engine.py`

**Interfaces:**
- Consumes: `engineering.model.MODE_DIVIDER`, `MODE_FIXED`, `MODE_EMITTER`, `MODES`, `MODE_LABELS`.
- Produces:
  - `SpiceInputs(vcc, rc, rl, cin, cout, amplitude, frequency, mode="divider", r1=None, r2=None, rb=None, re=None)`
  - `build_netlist(inputs: SpiceInputs, analysis: str) -> str` with mode-specific branches.

- [ ] **Step 1: Write the failing netlist tests**

Add to `tests/test_spice_engine.py`:

```python
def fixed_inputs():
    return SpiceInputs(
        vcc=12.0,
        rc=2.2e3,
        rl=10e3,
        cin=10e-6,
        cout=10e-6,
        amplitude=0.01,
        frequency=1e3,
        mode="fixed",
        rb=1e6,
    )


def emitter_inputs():
    return SpiceInputs(
        vcc=12.0,
        rc=2.2e3,
        rl=10e3,
        cin=10e-6,
        cout=10e-6,
        amplitude=0.01,
        frequency=1e3,
        mode="emitter",
        rb=1e6,
        re=1e3,
    )


def test_build_netlist_fixed_uses_rb_and_grounded_emitter():
    netlist = build_netlist(fixed_inputs(), ANALYSIS_DC)

    assert "RB vcc b 1000000" in netlist
    assert "VEMIT e 0 DC 0" in netlist
    assert "Q1 c b e 2N3904" in netlist
    assert "R1 vcc b" not in netlist
    assert "R2 b 0" not in netlist
    assert "RE e 0" not in netlist


def test_build_netlist_emitter_uses_rb_and_re():
    netlist = build_netlist(emitter_inputs(), ANALYSIS_DC)

    assert "RB vcc b 1000000" in netlist
    assert "RE e 0 1000" in netlist
    assert "Q1 c b e 2N3904" in netlist
    assert "R1 vcc b" not in netlist
    assert "R2 b 0" not in netlist
    assert "VEMIT" not in netlist


def test_build_netlist_rejects_fixed_without_rb():
    inputs = SpiceInputs(
        vcc=12.0,
        rc=2.2e3,
        rl=10e3,
        cin=10e-6,
        cout=10e-6,
        amplitude=0.01,
        frequency=1e3,
        mode="fixed",
    )

    with pytest.raises(SpiceError, match="RB is required"):
        build_netlist(inputs, ANALYSIS_DC)


def test_build_netlist_rejects_emitter_without_re():
    inputs = SpiceInputs(
        vcc=12.0,
        rc=2.2e3,
        rl=10e3,
        cin=10e-6,
        cout=10e-6,
        amplitude=0.01,
        frequency=1e3,
        mode="emitter",
        rb=1e6,
    )

    with pytest.raises(SpiceError, match="RE is required"):
        build_netlist(inputs, ANALYSIS_DC)


def test_run_dc_fixed_against_real_ngspice():
    if not spice_engine.ngspice_available():
        pytest.skip("ngspice is not installed")

    result = run(fixed_inputs(), ANALYSIS_DC)

    assert result.inputs.mode == "fixed"
    assert result.op is not None
    assert result.op.vce > 0
    assert result.op.vce < 12
    assert result.op.ve == pytest.approx(0.0, abs=1e-6)


def test_run_dc_emitter_against_real_ngspice():
    if not spice_engine.ngspice_available():
        pytest.skip("ngspice is not installed")

    result = run(emitter_inputs(), ANALYSIS_DC)

    assert result.inputs.mode == "emitter"
    assert result.op is not None
    assert result.op.vce > 0
    assert result.op.vce < 12
    assert result.op.ve > 0


@pytest.mark.parametrize("analysis", [ANALYSIS_AC, ANALYSIS_TRAN])
@pytest.mark.parametrize("factory", [fixed_inputs, emitter_inputs])
def test_run_ac_and_tran_all_modes_against_real_ngspice(analysis, factory):
    if not spice_engine.ngspice_available():
        pytest.skip("ngspice is not installed")

    result = run(factory(), analysis)

    if analysis == ANALYSIS_AC:
        assert len(result.ac) > 50
        assert all(math.isfinite(point.gain_db) for point in result.ac)
    else:
        assert len(result.tran) > 100
        assert all(math.isfinite(point.vout) for point in result.tran)
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `.\.venv\Scripts\python -m pytest tests\test_spice_engine.py -q`
Expected: failures for the missing `mode` field or missing mode-specific netlist lines.

- [ ] **Step 3: Implement the mode-aware data model and netlist**

In `spice_engine.py`:

```python
from engineering import model as bias_model

MODE_DIVIDER = bias_model.MODE_DIVIDER
MODE_FIXED = bias_model.MODE_FIXED
MODE_EMITTER = bias_model.MODE_EMITTER
MODES = bias_model.MODES
MODE_LABELS = bias_model.MODE_LABELS

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
```

Add a helper that raises `SpiceError` naming the missing field, then branch the netlist:

```python
def _require(value, name: str) -> float:
    if value is None:
        raise SpiceError(f"{name} is required for this circuit mode.")
    return value
```

- Divider: `R1 vcc b`, `R2 b 0`, `RE e 0`.
- Fixed: `RB vcc b`, `VEMIT e 0 DC 0`, no `R1`/`R2`/`RE`.
- Emitter: `RB vcc b`, `RE e 0`.
- Keep `CIN in b`, `COUT c out`, `RL out 0`, `Q1 c b e 2N3904` and the source common.
- Write the mode label into the netlist header.

- [ ] **Step 4: Run the engine tests to verify they pass**

Run: `.\.venv\Scripts\python -m pytest tests\test_spice_engine.py -q`
Expected: all tests pass, including the real-ngspice fixed/emitter runs.

- [ ] **Step 5: Commit**

```bash
git add spice_engine.py tests/test_spice_engine.py
git commit -m "feat: support fixed and emitter netlists in the simulator"
```

---

### Task 2: Mode-specific validation

**Files:**
- Modify: `spice_validation.py:30-45`, `spice_validation.py:64-144`
- Test: `tests/test_spice_validation.py`

**Interfaces:**
- Consumes: `spice_engine.SpiceInputs`, `spice_engine.MODE_*`.
- Produces:
  - `CIRCUIT_FIELDS: dict[str, tuple[str, ...]]`
  - `parse_circuit(raw: str | None) -> tuple[str | None, FieldError | None]`
  - `parse_spice_inputs(form, mode: str = "divider") -> tuple[SpiceInputs | None, list[FieldError]]`

- [ ] **Step 1: Write the failing validation tests**

Add to `tests/test_spice_validation.py`:

```python
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.\.venv\Scripts\python -m pytest tests\test_spice_validation.py -q`
Expected: failures for missing `parse_circuit`, missing `mode` argument, or missing `mode` field.

- [ ] **Step 3: Implement mode-specific fields and parsing**

In `spice_validation.py`:

```python
CIRCUIT_FIELDS = {
    "divider": ("vcc", "r1", "r2", "rc", "re", "rl", "cin", "cout", "amplitude", "frequency"),
    "fixed": ("vcc", "rb", "rc", "rl", "cin", "cout", "amplitude", "frequency"),
    "emitter": ("vcc", "rb", "re", "rc", "rl", "cin", "cout", "amplitude", "frequency"),
}
SPICE_FIELDS = CIRCUIT_FIELDS["divider"]
RESISTOR_FIELDS = ("r1", "r2", "rb", "rc", "re", "rl")
```

- `parse_circuit` mirrors `parse_analysis`, defaults to `divider`, returns `FieldError("mode", "Choose a supported circuit mode.")` for unknown values.
- `parse_spice_inputs(form, mode="divider")` reads only `CIRCUIT_FIELDS[mode]`, runs the existing range checks, then returns `SpiceInputs(mode=mode, **values)`.
- Unknown mode returns `None` with a `mode` error.

- [ ] **Step 4: Run the validation tests to verify they pass**

Run: `.\.venv\Scripts\python -m pytest tests\test_spice_validation.py -q`
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add spice_validation.py tests/test_spice_validation.py
git commit -m "feat: validate simulator fields per circuit mode"
```

---

### Task 3: Route and view-model mode switching

**Files:**
- Modify: `app.py:64-105`, `app.py:284-453`, `app.py:481-610`
- Test: `tests/test_simulator_routes.py`

**Interfaces:**
- Consumes: `spice_validation.CIRCUIT_FIELDS`, `parse_circuit`, `parse_spice_inputs(..., mode=...)`, `spice_engine.Mode`, `engineering.model`.
- Produces:
  - `GET /simulator?mode=fixed&analysis=dc`
  - `POST /simulator` with hidden `mode`
  - `_build_simulator_view(result, inputs)` returns `mode`, `mode_label`, and a mode-matched analytical reference.

- [ ] **Step 1: Write the failing route tests**

Add to `tests/test_simulator_routes.py`:

```python
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.\.venv\Scripts\python -m pytest tests\test_simulator_routes.py -q`
Expected: failures for missing mode-aware fields, mode forwarding, or reference selection.

- [ ] **Step 3: Implement route and view-model support**

In `app.py`:

- Add `"mode": "divider"` and `"rb": "1"` to `SPICE_DEFAULT_FORM`.
- Add `"rb": "MΩ"` to `SPICE_DEFAULT_UNITS`; add `"rb": RESISTOR_UNITS` to `SPICE_UNIT_CHOICES`.
- `render_simulator(...)` accepts `mode`, `mode_label`, `mode_choices` and passes them to the template.
- `simulator_get()` parses `mode` and `analysis`, defaults to divider/DC, and uses defaults for the selected mode.
- `simulator_post()` parses `mode` first, renders a form error for an unknown mode, then selects `CIRCUIT_FIELDS[mode]` for unit conversion and `parse_spice_inputs(..., mode=mode)`.
- `_build_simulator_view()` builds the analytical reference by mode:
  - divider → `model.BiasInputs(vcc, r1, r2, rc, re, beta, vbe)`
  - fixed → `model.FixedBiasInputs(vcc, rb, rc, beta, vbe)`
  - emitter → `model.EmitterBiasInputs(vcc, rb, re, rc, beta, vbe)`
  - call `evaluate.evaluate(reference, inputs.mode)`.
- Return `mode`, `mode_label`, and include a `Circuit` metric. Add the mode label to the analytical note.

- [ ] **Step 4: Run the route tests to verify they pass**

Run: `.\.venv\Scripts\python -m pytest tests\test_simulator_routes.py -q`
Expected: all route tests pass.

- [ ] **Step 5: Commit**

```bash
git add app.py tests/test_simulator_routes.py
git commit -m "feat: switch simulator results and references by circuit mode"
```

---

### Task 4: Mode selector, conditional fields and schematic

**Files:**
- Modify: `templates/simulator.html`
- Modify: `static/style.css`
- Test: `tests/test_simulator_routes.py`

**Interfaces:**
- Consumes: `mode`, `mode_label`, `mode_choices`, `values`, `units`, `unit_choices` from `render_simulator`.
- Produces: visible mode selector, mode-specific fields, mode-specific SVG, and mode label in results.

- [ ] **Step 1: Add failing template assertions**

Add to `tests/test_simulator_routes.py`:

```python
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.\.venv\Scripts\python -m pytest tests\test_simulator_routes.py -q`
Expected: the mode selector or conditional field assertions fail.

- [ ] **Step 3: Implement the template and CSS**

In `templates/simulator.html`:

- Add a GET form at the top of the `.sim-inputs` panel:

```html
<form method="get" action="{{ url_for('simulator_get') }}" class="mode-form sim-mode-form">
  <label class="field-label" for="mode">Circuit Mode</label>
  <select id="mode" name="mode" class="mode-select" onchange="this.form.submit()">
    {% for value, label in mode_choices %}
    <option value="{{ value }}" {% if value == mode %}selected{% endif %}>{{ label }}</option>
    {% endfor %}
  </select>
  <input type="hidden" name="analysis" value="{{ analysis }}">
  <noscript><button type="submit" class="btn-mode">Load circuit</button></noscript>
</form>
```

- Add `<input type="hidden" name="mode" value="{{ mode }}">` to the POST form.
- Show fields by mode:
  - divider: `VCC`, `R1`, `R2`, `RC`, `RE`, `RL`, `Cin`, `Cout`, source.
  - fixed: `VCC`, `RB`, `RC`, `RL`, `Cin`, `Cout`, source.
  - emitter: `VCC`, `RB`, `RE`, `RC`, `RL`, `Cin`, `Cout`, source.
- Reuse the existing `sim_field` macro; add `rb` to the unit choices passed from `app.py`.
- Make the SVG branch:
  - divider: current `R1`/`R2` and `RE`.
  - fixed: `RB` from VCC to base, emitter wire directly to ground.
  - emitter: `RB` from VCC to base and current `RE`.
  - Keep `RC`, `Cout`, `RL`, source and `Cin`.
  - Put `{{ mode_label }}` in the SVG `aria-label`.
- Change the run strip/result tag to show `{{ result.mode_label }} · {{ result.analysis_label }}`.
- Update the hint and goal band to mention the three modes.

In `static/style.css`:

```css
.sim-mode-form {
  padding: 0 1rem 0.75rem;
}
```

Reuse the existing `.mode-form` and `.mode-select` styles.

- [ ] **Step 4: Run the route tests and inspect the page**

Run: `.\.venv\Scripts\python -m pytest tests\test_simulator_routes.py -q`
Expected: all route tests pass.

Run the Flask app and open `/simulator?mode=divider`, `?mode=fixed`, `?mode=emitter` to confirm the fields and schematic change.

- [ ] **Step 5: Commit**

```bash
git add templates/simulator.html static/style.css tests/test_simulator_routes.py
git commit -m "feat: add circuit mode selector and schematics to the simulator"
```

---

### Task 5: Documentation, browser acceptance and final verification

**Files:**
- Modify: `README.md`
- Modify: `docs/validation.md`
- Test: full suite

- [ ] **Step 1: Update the README**

Document:
- The three simulator modes and their visible parameters.
- The fixed-bias emitter ground and unbypassed emitter `RE`.
- That all three modes run DC, AC and transient.
- The default mode remains voltage divider.
- Fixed bias can show a much larger gain because `RB` sets base current and the 2N3904 model has high `BF`; this is a real result.

- [ ] **Step 2: Run browser acceptance**

Restart Flask, then check:
- Divider regression: existing B1–B8 values still hold.
- Fixed mode: selector changes the schematic/fields; DC returns real values.
- Emitter mode: selector changes the schematic/fields; DC returns real values.
- Fixed AC and transient: Bode and waveform render.
- Emitter AC and transient: Bode and waveform render.
- Invalid mode: clear error, no ngspice run and no stale result.

Record expected/observed/status/evidence as B9–B13 in `docs/validation.md`.
Do not invent values; use the page output.

- [ ] **Step 3: Run the full suite and diff check**

Run:

```powershell
.\.venv\Scripts\python -m pytest -q
git diff --check
git status --short
```

Expected: all tests pass; no whitespace errors; only intended files changed.

- [ ] **Step 4: Commit the docs and final changes**

```bash
git add README.md docs/validation.md docs/superpowers/specs/2026-11-24-lab04-circuit-mode-switching-design.md docs/superpowers/plans/2026-11-24-lab04-circuit-mode-switching.md
git commit -m "docs: record Lab 04 circuit mode switching"
```

- [ ] **Step 5: Report the commit and ask before pushing**

Report the local commit SHA and the push command. Do not push without approval.
