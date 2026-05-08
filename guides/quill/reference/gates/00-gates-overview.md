# Gates — overview

The `quantum-circuit(..)` envelope is filled with **gates**. Quill ships
the constructors below; each has its own page in this folder.

| Function | Purpose |
| -------- | ------- |
| [`gate`](01-gate.md) | The base gate constructor (most general). |
| [`mqgate`](02-mqgate.md) | Multi-qubit / controlled gate spanning several wires. |
| [`meter`](03-meter.md) | Measurement symbol; can target a classical bit. |
| [`permute`](04-permute.md) | Permutation gate visualised as wire crossings. |
| [`phantom`](05-phantom.md) | Invisible gate for reserving space. |
| [`targ`](06-targ.md) | CNOT target (the `⊕` symbol). |
| [`phase`](07-phase.md) | Phase gate drawn as a labelled point on the wire. |
| [`swap`](08-swap.md) | Swap target (an `×`). |
| [`ctrl`](09-ctrl.md) | Filled control dot with a vertical wire. |

## Common arguments

Most gate constructors accept some subset of the following:

| Argument | Type | What it does |
| -------- | ---- | ------------ |
| `body` / first positional | `content` | The label inside the gate. |
| `x`, `y` | `auto | int` | Manual placement (column, row). |
| `fill` | `auto | none | color | gradient | tiling` | Fill of the gate box. |
| `stroke` | `auto | stroke` | Border stroke. |
| `radius` | `length | dictionary` | Border radius (per Typst's `rect`). |
| `width` | `auto | length` | Force a width. |
| `box` | `bool` | Draw the gate as a box (true) or transparent. |
| `label` | label-shape (see [tutorial 6](../../tutorial/06-labels.md)) | Labels around the gate. |
| `data` | any | Free-form data accessible from a custom `draw-function`. |
| `draw-function` | `(gate, draw-params) => content` | Custom renderer. |
| `size-hint` | function | Sizing hint paired with `draw-function`. |

`mqgate(...)` adds `n`, `target`, `wire-count`, `inputs`, `outputs`,
`extent`, `pass-through`, `wire-label`, and `size-all-wires`. The
control-style gates (`ctrl`, `targ`, `swap`) take a relative `..n`
positional and a `wire-label`.

## Gate vs. shorthand

These are equivalent inside `quantum-circuit(...)`:

```typst
gate($H$)
$H$
```

The gate body is content, so any Typst content (math, image, table) is
allowed. Use `gate(body, ...)` when you need to set non-default
options; otherwise the inline math shorthand is fine.

## Related

- Decorations (sticks, slices, groups): [`reference/decorations/`](../decorations/00-decorations-overview.md)
- Custom rendering: [`reference/custom-gates/`](../custom-gates/00-custom-gates-overview.md)
- Gallery of every visual symbol: [`gallery/`](../../gallery/00-gallery-overview.md)
