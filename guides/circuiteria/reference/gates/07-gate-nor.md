# `gates.gate-nor()` — NOR Gate

Draws a NOR gate (the OR shape with a bubble on the output). Also
available as `element.gate-nor()`.

```text
gates.gate-nor(x: 0, y: 0, w: 1.5, h: 1.5)
gates.gate-nor(x: 3, y: 0, w: 1.5, h: 1.5, inverted: "all")
```

## Signature

```text
gate-nor(
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
| `<id>-port-in0`, `<id>-port-in1`, … `<id>-port-in<inputs-1>` | west | One per input. |
| `<id>-port-out` | east | The output (drawn with the bubble). |

## Pitfalls

- Like NAND, the output bubble is part of the symbol; the port anchor
  still points at the rightmost tip of the bubble.
- `inverted: ("out",)` adds a second bubble — typically not what you
  want.

## Example

See [`examples/07-gate-nor/07-gate-nor.typ`](./examples/07-gate-nor/07-gate-nor.typ).

## Related

- [`06-gate-or.md`](./06-gate-or.md) — the non-inverted sibling.
- [`03-gate-nand.md`](./03-gate-nand.md) — the AND-side equivalent.
