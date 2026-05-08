# 1 — Introduction

Quill is a Typst package for drawing **quantum-circuit diagrams**. If
you have used `qcircuit` or `quantikz` in LaTeX, the syntax will feel
very familiar. The main differences are:

- The math environment is **not** entered automatically inside a gate, so
  any Typst content (math, images, even tables) is allowed as a gate body.
- Live preview makes it trivial to iterate on layout.
- A few names are tightened: `[\\ ]` to break to a new wire, plain integers
  for empty cells, length values for gutters.

## Install

```typst
#import "@preview/quill:0.7.2": *
```

A single wildcard import is the most ergonomic for circuit-heavy
documents. The Tequila DSL is a separate submodule:

```typst
#import "@preview/quill:0.7.2": tequila as tq
```

## Your first circuit

```typst
#quantum-circuit(
  1, gate($H$), phase($theta.alt$), meter(), 1
)
```

Ordering left-to-right: an empty cell with a wire, a Hadamard gate, a
phase gate showing `θ`, a measurement meter, then another empty cell.

See [`examples/01-introduction/01-introduction.typ`](examples/01-introduction/01-introduction.typ).

## What you can put in `quantum-circuit`

Any of the following items is a valid child of `quantum-circuit(..)`:

| Item | Meaning |
| ---- | ------- |
| `gate(...)`, `mqgate(...)`, `meter(...)`, `ctrl(...)`, … | A gate. |
| `[\\ ]` | Break the current wire — start a new row. |
| Integers (`1`, `3`) | That many empty wire cells. |
| Lengths (`5pt`, `10pt`) | Horizontal gutter (after `[\\ ]` it becomes a vertical gutter). |
| `setwire(count, stroke, wire-distance)` | Change wire style from this point on. |
| `slice(...)`, `gategroup(...)`, `annotate(...)` | Decorations laid over the circuit. |
| Plain content / strings | Placed centred on the wire. |
| `lstick(...)`, `midstick(...)`, `rstick(...)` | Labels at the wire start, middle, end. |

## Next

Continue with [`02-basics.md`](02-basics.md) — wires and the gate shorthand.
