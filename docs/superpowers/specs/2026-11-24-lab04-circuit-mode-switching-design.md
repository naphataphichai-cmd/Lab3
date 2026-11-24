# Lab 04 — Circuit Mode Switching (Divider / Fixed / Emitter) — Design

## Intent

Extend the existing Lab 04 `/simulator` page so it can switch between the three
Lab 03 bias circuits instead of only the voltage-divider reference:

- **Voltage Divider Bias** — `R1` from VCC to base, `R2` from base to ground,
  `RE` from emitter to ground.
- **Fixed Bias** — `RB` from VCC to base, emitter tied directly to ground.
- **Emitter Bias (single supply)** — `RB` from VCC to base, `RE` from emitter
  to ground (no bypass capacitor).

The selected mode must change the schematic, visible input fields, generated
ngspice netlist, DC/AC/transient results, and the Lab 03 analytical reference.
It must not merely change a label.

This is a small extension to the approved Lab 04 v1 design; it supersedes the
v1 scope limit of one reference divider circuit. The Lab 03 page and all three
of its analytical modes remain unchanged.

## Goals

- Add one circuit-mode selector to `/simulator` with the same three modes and
  labels as Lab 03.
- Generate a correct real ngspice netlist for each topology and run DC, AC and
  transient for all three modes.
- Show only the parameters that the selected circuit uses, with units.
- Compare each SPICE result against the matching Lab 03 analytical mode
  (`divider`, `fixed`, `emitter`), using the existing `β = 100`, `VBE = 0.70 V`
  reference assumptions.
- Preserve the existing divider default values, plots, provenance and tests.
- Add unit, route and real-ngspice integration tests for the new modes.
- Record the new browser acceptance cases in `docs/validation.md`.

## Non-goals

- Arbitrary circuit entry, netlist import, or a schematic editor.
- A bypass capacitor for `RE` in emitter bias; the topology follows Lab 03.
- Changing Lab 03 formulas, routes, templates or acceptance results.
- AC/transient analysis on the Lab 03 page.
- Temperature sweeps or measured-device model extraction.

## Approaches considered

1. **One `/simulator` page with a GET mode selector (chosen).** Reuses the
   existing page, analysis tabs, plots and provenance. The mode is a normal
   server-rendered parameter, so the netlist and results cannot drift from the
   visible schematic.
2. **Separate pages per mode.** Clear URLs, but duplicates the form, results,
   plots and tests. Rejected for this small extension.
3. **Client-side field switching only.** Keeps the page from reloading, but the
   server would still need a mode-specific netlist and the UI would have two
   sources of truth. Rejected.

## Design

### Data model

`SpiceInputs` gains a `mode` field and an optional `rb`. `r1`, `r2` and `re`
become optional because they are not present in every topology. Existing
divider call sites keep working because they use keyword arguments and default
to `mode="divider"`.

```python
SpiceInputs(
    vcc, rc, rl, cin, cout, amplitude, frequency,
    mode="divider",
    r1=None, r2=None, rb=None, re=None,
)
```

Mode constants and labels are taken from `engineering.model` so the simulator
and Lab 03 cannot disagree.

### Netlist

`build_netlist(inputs, analysis)` branches on `inputs.mode`:

| Mode | Bias network | Emitter path |
|---|---|---|
| `divider` | `R1 vcc b`, `R2 b 0` | `RE e 0` |
| `fixed` | `RB vcc b` | `VEMIT e 0 DC 0` (0 V source to ground) |
| `emitter` | `RB vcc b` | `RE e 0` |

`VEMIT` gives the fixed-bias emitter a DC path to ground without changing the
topology, and keeps node `e` available for the existing `v(e)` operating-point
print. All modes keep `RC`, `RL`, `CIN`, `COUT`, `Q1`, the source and the
2N3904 model. Missing mode-specific values raise a clear `SpiceError` instead
of a `TypeError`.

### Validation

`spice_validation` gets:

- `CIRCUIT_FIELDS`: mode → required form fields.
- `parse_circuit(raw)` with a default of `divider`.
- `parse_spice_inputs(form, mode="divider")`, which reads only the fields for
  that mode and constructs `SpiceInputs(mode=mode, ...)`.
- The existing `SPICE_FIELDS` alias stays for divider compatibility.

The same electrical ranges apply to all modes. Extra fields from a previous
mode are ignored.

### Route and view model

`GET /simulator` accepts `mode` and `analysis`. `POST /simulator` reads the
hidden `mode` field, validates only that topology's fields, runs ngspice, and
builds the matching analytical reference:

- divider → `model.BiasInputs`
- fixed → `model.FixedBiasInputs`
- emitter → `model.EmitterBiasInputs`

The result view exposes the mode label so the run strip, result tag and
analytical note identify the selected circuit. SPICE and Lab 03 values stay in
separate columns, as in v1.

### UI

- A GET form at the top of the input panel: “Circuit Mode” select, current
  `analysis` preserved in a hidden field, and a `<noscript>` button.
- The POST form carries the selected mode in a hidden field.
- Visible fields follow the mode:
  - divider: `VCC, R1, R2, RC, RE, RL, Cin, Cout, amplitude, frequency`
  - fixed: `VCC, RB, RC, RL, Cin, Cout, amplitude, frequency`
  - emitter: `VCC, RB, RE, RC, RL, Cin, Cout, amplitude, frequency`
- The SVG schematic branches the same way as the Lab 03 page: divider uses
  `R1/R2`, fixed uses `RB` and a grounded emitter, emitter uses `RB/RE`.
- Analysis tabs, plots, netlist/log details and responsive layout are unchanged.

### Verification

- Unit tests for mode parsing, mode-specific validation, netlist contents and
  missing-field errors.
- Route tests for GET field visibility, POST mode propagation, fixed/emitter
  analytical references and invalid modes.
- Real-ngspice integration tests for DC, AC and transient on all three modes.
- Browser acceptance after the existing B1–B8: mode switch, fixed DC, emitter
  DC, fixed/emitter AC and transient, and divider regression.
- Full `pytest -q`; no Lab 03 regression.

## Calls made for this implementation

- Reuse Lab 03 mode names and labels rather than inventing new ones.
- Use Lab 03 topology exactly; emitter `RE` is unbypassed.
- Use a 0 V source for the fixed-bias emitter ground so the existing operating
  point parser keeps working.
- Keep the shared 10 mV peak default; fixed bias may show a larger, possibly
  clipped output, which is a real simulator result rather than a hidden error.
- Keep the mode selector server-rendered (GET) to match Lab 03 and avoid a
  client-side source of truth.
