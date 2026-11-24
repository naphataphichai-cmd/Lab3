# Lab 03 — Browser Acceptance Record (A1–A5)

- GitHub: <https://github.com/naphataphichai-cmd/Lab3>
- Commit: `27700bba838c487dfb7dafb3491bb2f3bd2c2536`

Shared inputs for every case: `VCC = 12 V`, `RC = 2.2 kΩ`, `β = 100`,
`VBE = 0.70 V`. Expected values below were calculated by hand from the Lab 03
equations before running the app, not read from the code.

Tolerance used: `±0.01 mA` for `IC` and `±0.02 V` for `VCE`, compared with the
unrounded hand values. Values on the page are shown with 4 significant digits.

| Case | Mode and inputs | Expected | Observed on page | Method | Status |
|---|---|---|---|---|---|
| A1 · original mode | Divider · `R1 = 100 kΩ`, `R2 = 22 kΩ`, `RE = 1 kΩ` | `IC = 1.2298 mA`, `VCE = 8.0522 V` (same as Lab 02) | `IC = 1.23 mA`, `VCE = 8.052 V`, `✓ MATCH` | OpenCode Browser | PASS |
| A2 · Fixed | Fixed · `RB = 1 MΩ` | `IC = 1.1300 mA`, `VCE = 9.5140 V` | `IC = 1.13 mA`, `VCE = 9.514 V`, `✓ MATCH` | OpenCode Browser | PASS |
| A3 · Emitter | Emitter · `RB = 1 MΩ`, `RE = 1 kΩ` | `IC = 1.0263 mA`, `VCE = 8.7054 V` | `IC = 1.026 mA`, `VCE = 8.705 V`, `✓ MATCH` | OpenCode Browser | PASS |
| A4 · one value changed | Emitter · as A3 with `RE = 2 kΩ` | `IC = 0.9401 mA`, `VCE = 8.0328 V`; `IC` must fall versus A3 | `IC = 940.1 µA`, `VCE = 8.033 V`; lower than A3 | OpenCode Browser | PASS |
| A5 · bad input | Fixed · `RB = 0` | Range message for `RB`, no result from the previous run | `Must be between 1 mΩ and 10 MΩ.`; result table shows `--`, no `MATCH` badge | OpenCode Browser | PASS |

Method notes: all five cases were run in the in-app Chromium browser against
`http://127.0.0.1:5000/`, with the mode loaded from `/?mode=...`, values entered
in the page form, and the "Calculate DC Bias" button clicked. The A1–A4 values
above were read from the results panel after the page reloaded. A5 was read from
the field error and the empty result table after submitting.

Evidence: `docs/lab03-a3-emitter.jpeg` is the full-page capture of A3, showing
the selected mode, `IC = 1.026 mA`, `VCE = 8.705 V`, and the independent
(nodal) column agreeing to `2.2e-13` or better.

Expected values were compared with the page using `±0.01 mA` for `IC` and
`±0.02 V` for `VCE`; all observed values are inside those bands.

## Hand calculations

### A1 — Voltage Divider

```text
VBB = 12 · 22 / (100 + 22) = 2.163934 V
RB  = 100 · 22 / (100 + 22) = 18.032787 kΩ
IB  = (2.163934 − 0.70) / (18032.787 + 101 · 1000) = 12.298 µA
IC  = 100 · 12.298 µA = 1.2298 mA
VE  = 101 · 12.298 µA · 1 kΩ = 1.2421 V
VC  = 12 − 1.2298 mA · 2.2 kΩ = 9.2944 V
VCE = 9.2944 − 1.2421 = 8.0522 V
```

### A2 — Fixed Bias

```text
IB  = (12 − 0.70) / 1 MΩ = 11.30 µA
IC  = 100 · 11.30 µA = 1.130 mA
VC  = 12 − 1.130 mA · 2.2 kΩ = 9.514 V
VE  = 0 V  →  VCE = 9.514 V
```

### A3 — Emitter Bias

```text
IB  = (12 − 0.70) / (1 MΩ + 101 · 1 kΩ) = 11.3 / 1.101 MΩ = 10.263 µA
IC  = 100 · 10.263 µA = 1.0263 mA
IE  = 101 · 10.263 µA = 1.0366 mA
VE  = 1.0366 mA · 1 kΩ = 1.0366 V
VC  = 12 − 1.0263 mA · 2.2 kΩ = 9.7421 V
VCE = 9.7421 − 1.0366 = 8.7054 V
```

### A4 — Emitter with `RE = 2 kΩ`

```text
IB  = 11.3 / (1 MΩ + 101 · 2 kΩ) = 11.3 / 1.202 MΩ = 9.401 µA
IC  = 100 · 9.401 µA = 0.9401 mA
VE  = 101 · 9.401 µA · 2 kΩ = 1.8990 V
VC  = 12 − 0.9401 mA · 2.2 kΩ = 9.9318 V
VCE = 9.9318 − 1.8990 = 8.0328 V
```

Prediction before running A4: raising `RE` raises the emitter degeneration in
the base loop, so `IB` and `IC` fall while `VE` rises. `IC` must be lower than
A3's `1.0263 mA`.

### A5 — `RB = 0`

`0 Ω` is below the accepted `1 mΩ` minimum, so the app must show the resistor
range message next to `RB` and must not display A2's result as the result of
this run.

---

# Lab 04 — Browser Acceptance Record (B1–B8)

- Page under test: `http://127.0.0.1:5000/simulator`
- Engine reported by the page: `ngspice-47`
- BJT model reported by the page: `2N3904` (standard Motorola Gummel-Poon card)
- Method: OpenCode Browser in the in-app Chromium session, with the Flask
  development server on port 5000. Values were entered in the page form and
  the "Run simulation" button was submitted; the observations below were read
  from the result metrics, result table, SVG, and error elements after reload.

Baseline circuit for B2, B4, B5: `VCC = 12 V`, `R1 = 100 kΩ`, `R2 = 22 kΩ`,
`RC = 2.2 kΩ`, `RE = 1 kΩ`, `RL = 10 kΩ`, `Cin = Cout = 10 µF`,
`amplitude = 10 mV peak`, `frequency = 1 kHz`.

Expected results were stated before each run from the circuit and the analysis
definition (not copied from the app's output). SPICE DC values are expected to
differ from the Lab 03 analytical reference because the 2N3904 model and the
`β = 100`, `VBE = 0.70 V` assumptions are different.

| Case | Check | Expected | Observed | Status |
|---|---|---|---|---|
| B1 · Lab 03 regression | Fixed, Emitter and Divider modes still load and calculate after adding Lab 04 | Same A1–A3 values as before; `MATCH` shown in every mode | Fixed `IC = 1.13 mA`, `VCE = 9.514 V`; Emitter `IC = 1.026 mA`, `VCE = 8.705 V`; Divider `IC = 1.23 mA`, `VCE = 8.052 V`; all `MATCH` | PASS |
| B2 · DC `.op` | Run DC on the baseline circuit | Real ngspice result, finite `VB, VE, VC, VCE, IC, IB, IE`, forward-active, `0 < VCE < VCC` | `VB = 2.004 V`, `VE = 1.333 V`, `VC = 9.087 V`, `VCE = 7.754 V`, `IB = 8.887 µA`, `IC = 1.324 mA`, `IE = 1.333 mA`; region `active`; engine `ngspice-47`; model `2N3904` | PASS |
| B3 · one value changed | Baseline DC with `RE = 2 kΩ` | More emitter degeneration: `IC` falls and `VCE` rises versus B2; still active | `IC = 705.3 µA`, `VCE = 9.032 V`; lower `IC`, higher `VCE`; region `active` | PASS |
| B4 · AC Bode | Run AC on the baseline circuit | Two plotted curves (gain and phase); gain at 1 kHz in single-digit positive dB; phase near −180°; low-frequency cutoff visible; `fH` honestly reported as outside the sweep | `4.89 dB (1.756×)` at 1 kHz; phase `−179.9°`; midband `4.89 dB`; `fL ≈ 2 Hz`; `fH` not in sweep; sweep `100 mHz – 100 MHz`; SVG contains 2 polylines | PASS |
| B5 · transient | Run transient on the baseline circuit | Two waveforms; `Vin pp = 20 mV` for a 10 mV peak source; `Vout` several tens of mV; output inverted; 5-cycle window | `Vin pp = 20 mV`; `Vout pp = 35.1 mV`; `Vout/Vin = 1.76×`; `inverted (≈180°)`; window `0 – 5 ms`; SVG contains 2 polylines | PASS |
| B6 · source changed | Transient with amplitude `20 mV`, then frequency `2 kHz` at `10 mV` | Doubling amplitude doubles both peak-to-peak values and keeps gain; doubling frequency halves the 5-cycle window and keeps gain | At `20 mV`: `Vin pp = 40 mV`, `Vout pp = 70.2 mV`, gain `1.76×`; at `2 kHz`: window `0 – 2.5 ms`, `Vin pp = 20 mV`, `Vout pp = 35.1 mV`, gain `1.76×` | PASS |
| B7 · bad input | DC with `RE = 0` | Field-level range error; no `SUCCESS`, no result table, no plot, no stale previous result | `Must be between 1 mΩ and 10 MΩ.` next to `RE`; no `SUCCESS`; no result table; no SVG plot | PASS |
| B8 · layout | Inspect the simulator at desktop and phone widths | Panels fit without horizontal overflow; three-column layout on desktop; stacked layout at phone width | At `1296 × 886`: grid columns `340 px / 517 px / 360 px`, document `scrollWidth = 1281 px` (< viewport), no horizontal overflow. At a `390 × 844` same-origin iframe: one column `343 px`, panels stacked in order inputs → plots → results, `scrollWidth = 375 px`, no horizontal overflow. Pixel screenshot capture was unavailable (tool requires a visible desktop window). | PASS |

### B1–B8 notes

- B1 is the explicit regression check that adding `/simulator` did not change
  the Lab 03 analytical results; the three modes were loaded and submitted one
  after another in the same browser session.
- B2–B6 each triggered a fresh ngspice run. The netlist and ngspice log were
  available in the collapsible `<details>` blocks, and the page showed the
  engine and model on every successful run.
- B7 confirms the validation path runs before the engine: no ngspice result,
  table, or plot is rendered for the rejected input.
- B8 used two live width checks. Desktop metrics were read from the page at
  `1296 × 886`. Because `window.resizeTo()` did not change this browser tab's
  viewport, the phone-width check loaded the same page in a `390 × 844`
  same-origin iframe and measured the computed grid inside it: the `820 px`
  breakpoint produced one column, stacked panels, and no horizontal overflow.
  No pixel screenshot is attached because `browser.screenshot` reported
  "Screenshot needs a visible tab"; the layout evidence is the live DOM/CSS
  metrics above.

---

# Lab 04 Circuit Mode Switching — Browser Acceptance (B9–B13)

Shared baseline for the mode checks: `VCC = 12 V`, `RC = 2.2 kΩ`,
`RL = 10 kΩ`, `Cin = Cout = 10 µF`, `amplitude = 10 mV peak`,
`frequency = 1 kHz`. Fixed mode adds `RB = 1 MΩ`; emitter mode adds
`RB = 1 MΩ` and `RE = 1 kΩ`. Divider mode keeps `R1 = 100 kΩ`,
`R2 = 22 kΩ`, `RE = 1 kΩ`.

| Case | Check | Expected | Observed | Status |
|---|---|---|---|---|
| B9 · mode selector | Switching the dropdown changes visible fields, schematic and labels without leaving the page's analysis selection | Fixed shows `RB` and no `R1/R2/RE`; emitter shows `RB` and `RE`; divider shows `R1/R2/RE`; `analysis` is preserved | Fixed fields `VCC, RB, RC, RL, Cin, Cout, amplitude, frequency`; emitter also `RE`; divider `VCC, R1, R2, RC, RE, RL, Cin, Cout, amplitude, frequency`; mode label changes on the page | PASS |
| B10 · Fixed DC | Run DC on fixed bias | Real ngspice result, active region, emitter at ground | `VB = 0.6781 V`, `VE = 0 V`, `VC = 8.148 V`, `VCE = 8.148 V`, `IB = 11.32 µA`, `IC = 1.751 mA`, `IE = 1.762 mA`; analytical reference `IC = 1.13 mA`, `VCE = 9.514 V` | PASS |
| B11 · Fixed AC and transient | Run AC and transient on fixed bias | High gain, two Bode curves, two waveform traces, inverted output | AC `41.17 dB (114.364×)`, phase `−179.6°`, `fL ≈ 6.31 Hz`, `fH ≈ 28.2 MHz`; transient `Vin pp = 20 mV`, `Vout pp = 2.33 V`, `116.33×`, inverted, window `0 – 5 ms`; 2 polylines in each plot | PASS |
| B12 · Emitter DC/AC/transient | Run all three analyses on emitter bias | Real ngspice results, active region, `VE > 0`, gain similar to divider | DC `VB = 2.161 V`, `VE = 1.487 V`, `VC = 8.750 V`, `VCE = 7.263 V`, `IC = 1.477 mA`; AC `4.91 dB (1.759×)`, phase `−179.9°`, `fL ≈ 1.41 Hz`; transient `Vin pp = 20 mV`, `Vout pp = 35.2 mV`, `1.76×`, inverted; analytical reference `IC = 1.026 mA`, `VCE = 8.705 V` | PASS |
| B13 · invalid mode | Submit `mode=noise` | Clear mode error, no `SUCCESS`, no result table, no plot, no ngspice run | `Choose a supported circuit mode.` banner; no `SUCCESS`; no result table; no SVG plot | PASS |

### B9–B13 notes

- B9 was checked by loading `/simulator?mode=fixed`, `?mode=emitter` and
  `?mode=divider` in the same browser session and reading the visible field
  list and schematic labels.
- B10–B12 each triggered fresh ngspice runs. The netlist and run log were
  available in the collapsible `<details>` blocks, and the page showed the
  selected mode, engine and model on every successful run.
- B13 confirms that an unknown mode is rejected before unit conversion,
  validation and ngspice execution.
- Divider regression was re-checked after adding the mode selector: the
  B2–B6 values still match the earlier record.
- The exact B2–B6 values above were read from the page after each run; none of
  them is a hard-coded success value. Changing `RE`, amplitude, or frequency
  changed the parsed ngspice output and the displayed metrics as expected.
