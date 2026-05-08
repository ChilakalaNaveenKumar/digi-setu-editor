# `gates.gate-buf()` — Buffer Gate

Draws a buffer gate (the simple triangle symbol — output is the same as
input). Also available as `element.gate-buf()`.

```text
gates.gate-buf(x: 0, y: 0, w: 1.5, h: 1.5)
gates.gate-buf(x: 3, y: 0, w: 1.5, h: 1.5, inverted: "all")
```

## Signature

```text
gate-buf(
  x,
  y,
  w,
  h,
  inputs,
  fill,
  stroke,
  id,
  inverted,
  debug,
) -> none
```

For descriptions of all arguments, see [`gate()`](./01-gate.md).

## Built-in ports

| Anchor | Side | Notes |
| ------ | ---- | ----- |
| `<id>-port-in0` | west | The single input (`inputs` is silently ignored — a buffer always has one input). |
| `<id>-port-out` | east | The output. |

## Pitfalls

- `inputs:` is accepted (so the signature stays uniform with the rest of
  the gate family) but is **ignored** — `gate-buf` always has exactly one
  input.
- A buffer with `inverted: "all"` is visually the same as
  [`gate-not`](./05-gate-not.md). Prefer the explicit `gate-not` for
  clarity in schematics.

## Example

See [`examples/04-gate-buf/04-gate-buf.typ`](./examples/04-gate-buf/04-gate-buf.typ).

## Related

- [`05-gate-not.md`](./05-gate-not.md) — the inverted-output sibling.
