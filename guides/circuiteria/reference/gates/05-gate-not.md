# `gates.gate-not()` — NOT Gate (Inverter)

Draws a NOT gate / inverter (triangle with a bubble on the output). Also
available as `element.gate-not()`.

```text
gates.gate-not(x: 0, y: 0, w: 1.5, h: 1.5)
gates.gate-not(x: 3, y: 0, w: 1.5, h: 1.5, inverted: "all")
```

## Signature

```text
gate-not(
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
| `<id>-port-in0` | west | The single input (`inputs` is silently ignored — a NOT gate always has one input). |
| `<id>-port-out` | east | The output (drawn with the bubble). |

## Pitfalls

- `inputs:` is accepted but ignored — a NOT gate always has one input.
- The output bubble is part of the symbol; the port anchor still points
  at the rightmost tip of the bubble.
- `inverted: "all"` adds an extra bubble on the input side too.

## Example

See [`examples/05-gate-not/05-gate-not.typ`](./examples/05-gate-not/05-gate-not.typ).

## Related

- [`04-gate-buf.md`](./04-gate-buf.md) — the buffer (no bubble).
