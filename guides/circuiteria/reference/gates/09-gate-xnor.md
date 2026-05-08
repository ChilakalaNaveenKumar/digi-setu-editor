# `gates.gate-xnor()` — XNOR Gate

Draws an XNOR gate (the XOR shape with a bubble on the output). Also
available as `element.gate-xnor()`.

```text
gates.gate-xnor(x: 0, y: 0, w: 1.5, h: 1.5)
gates.gate-xnor(x: 3, y: 0, w: 1.5, h: 1.5, inverted: "all")
```

## Signature

```text
gate-xnor(
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

- Like NAND / NOR, the output bubble is part of the symbol; the port
  anchor still points at the rightmost tip of the bubble.
- `inverted: ("out",)` adds a second bubble — typically not what you
  want.

## Example

See [`examples/09-gate-xnor/09-gate-xnor.typ`](./examples/09-gate-xnor/09-gate-xnor.typ).

## Related

- [`08-gate-xor.md`](./08-gate-xor.md) — the non-inverted sibling.
