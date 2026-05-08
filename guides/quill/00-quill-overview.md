# Quill — quantum circuit diagrams for Typst

[Quill](https://github.com/Mc-Zen/quill) is a Typst package for drawing
quantum-circuit diagrams. The syntax is inspired by `qcircuit` and
`quantikz` (LaTeX) but cleans things up to feel native to Typst: no
implicit math mode, content-first gates, and live preview.

This sub-corpus mirrors the official Quill manual (v0.7.2) one concept
per page with a runnable `.typ` example for each. **Always cite paths
under `guides/quill/`** for Quill questions — the rest of `guides/` is
core Typst or a different package.

## Install / import

```typst
#import "@preview/quill:0.7.2": *
```

The most common imports are `quantum-circuit`, `gate`, `mqgate`, `meter`,
`ctrl`, `targ`, `swap`, `phase`, `permute`, `nwire`, `setwire`,
`lstick`, `rstick`, `midstick`, `gategroup`, `slice`, `annotate`,
`phantom`, and `meter-symbol`. The Tequila DSL lives in the `tequila`
submodule (`#import "@preview/quill:0.7.2": tequila as tq`).

## Folder layout

| Folder | Contents |
| ------ | -------- |
| `tutorial/` | Step-by-step intro: basics → wires → labels → groups → styling → fine-tuning → annotations → custom gates. |
| `reference/quantum-circuit/` | The `quantum-circuit()` envelope and every layout knob (row/column spacing, color, scale, baseline, …). |
| `reference/gates/` | Every gate constructor: `gate`, `mqgate`, `meter`, `ctrl`, `targ`, `swap`, `phase`, `permute`, `phantom`. |
| `reference/decorations/` | Wire & label commands: `lstick`, `rstick`, `midstick`, `nwire`, `setwire`, `gategroup`, `slice`, `annotate`. |
| `reference/styling/` | Dark-mode, gate-padding, equal-row-heights, and other circuit-wide styling recipes. |
| `reference/custom-gates/` | Writing your own `draw-function` for `gate()` / `mqgate()`. |
| `reference/tequila/` | The `tequila` Qiskit-style submodule (`build`, `graph-state`, `qft`, gate constructors). |
| `gallery/` | Gate gallery — one runnable example per visual symbol. |
| `demos/` | Full reproduction figures from Nielsen & Chuang (teleportation, QPE, QFT, Shor 9-qubit, …). |

## Reading order (suggested)

1. `tutorial/01-introduction.md` — what Quill does, install, first circuit.
2. `tutorial/02-basics.md` — gates, wires, plain integers, `[\\ ]` row breaks.
3. `tutorial/03-multi-qubit-and-labels.md` — `mqgate`, `lstick`, `rstick`.
4. `tutorial/04-wires.md` — `setwire`, classical / bundled wires.
5. `tutorial/05-slices-and-groups.md` — `slice`, `gategroup`.
6. `tutorial/06-labels.md` — full label dictionary (`pos`, `dx`, `dy`).
7. `tutorial/07-gate-placement.md` — manual `x:` / `y:` placement.
8. `tutorial/08-styling.md` — `wire`, `color`, `fill`, `scale`.
9. `tutorial/09-fine-tuning.md` — length items, gutters, vertical space.
10. `tutorial/10-annotations.md` — `annotate(columns, rows, callback)`.
11. `tutorial/11-custom-gates.md` — writing a `draw-function`.

After the tutorial, every reference page lists its function signature,
defaults, pitfalls, and links to a paired `.typ` example.

## Cross-references

- Tequila is **inside** Quill; see `reference/tequila/` rather than
  searching the wider corpus.
- Quill is independent of CeTZ — do not pull `guides/cetz/` paths for
  circuit questions.
- Use `search_quill_docs` (not `search_typst_docs`) to find any of these
  pages.
