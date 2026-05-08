# `mark` — Arrow / Line-End Marks

`cetz.mark` is the engine that places marks (arrowheads, bars, dots,
custom decorations) along the start, end, or interior of a path. It is
fed by `(mark: (...))` arguments on shapes such as `line`, `arc`, and
`bezier`.

The module is exposed at `cetz.mark.<fn>`.

## Functions

| File | Function |
| --- | --- |
| [`01-check-mark.md`](./01-check-mark.md) | `check-mark()` |
| [`02-process-style.md`](./02-process-style.md) | `process-style()` |
| [`03-place-mark-on-path.md`](./03-place-mark-on-path.md) | `place-mark-on-path()` |
| [`04-place-marks-along-path.md`](./04-place-marks-along-path.md) | `place-marks-along-path()` |

> **Most users never call these directly.** End-user code drives marks
> via the `mark` shape and the `mark:` style key on path shapes; the
> functions in this module are how that machinery is implemented.

## Related

- [`mark`](../../shapes/05-mark.md) — the user-facing standalone mark shape
- [`register-mark`](../../styling/04-register-mark.md) — register a custom
  mark symbol for use anywhere a mark name is accepted
- See the `mark style` entry in the
  [Types Glossary](../../../types/00-types-overview.md) for the full
  shape of the dictionary `check-mark` validates
