# `styles` — Style Resolution & Folding

`cetz.styles` is the engine that turns the per-call `(fill: ..., stroke: ...,
…)` arguments and the inherited style tree into a single concrete style
dictionary used to render an element.

The module is exposed at `cetz.styles.<fn>`.

## Functions

| File | Function |
| --- | --- |
| [`01-resolve.md`](./01-resolve.md) | `resolve()` |
| [`02-merge.md`](./02-merge.md) | `merge()` |

## Related

- Tutorial: [Styling](../../../tutorial/05-styling.md) — the style
  inheritance model, root-style keys, per-call overrides
- [`set-style`](../../styling/01-set-style.md) — the user-facing style root setter
- [Types — `style`](../../../types/00-types-overview.md)
