# `util.colors` — Predefined Colour Palette

A small dictionary of ready-made colours, intended as default `fill:`
values for blocks and groups so that diagrams keep a consistent
look-and-feel.

```text
util.colors.orange   util.colors.yellow   util.colors.green
util.colors.pink     util.colors.purple   util.colors.blue
```

## Signature

```text
colors: dictionary
```

It is a *variable*, not a function — read with member access
(`util.colors.<name>`). The keys are:

| Key | Use |
| --- | --- |
| `orange` | Warm fill used in the manual's example for arithmetic blocks. |
| `yellow` | High-contrast highlight. |
| `green` | Used in the `group()` example for the upper block. |
| `pink` | Pastel highlight. |
| `purple` | Pastel highlight. |
| `blue` | Used in the `group()` example for the right-hand block. |

## Pitfalls

- These are *paint values* — pass them as `fill: util.colors.green`. Do
  not stringify them.
- The palette is small by design; for any colour outside it, use Typst's
  built-in colour constructors (`rgb("#abcdef")`, `oklch(...)`, etc.).

## Example

See [`examples/04-colors/04-colors.typ`](./examples/04-colors/04-colors.typ).

## Related

- [`../element/06-group.md`](../element/06-group.md) — the manual's
  reference example colours its inner blocks with `util.colors.green`,
  `util.colors.orange`, and `util.colors.blue`.
