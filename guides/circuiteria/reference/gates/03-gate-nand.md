# `gates.gate-nand()` — NAND Gate

Draws a NAND gate (the AND D-shape with a bubble on the output). Also
available as `element.gate-nand()`.

```text
gates.gate-nand(x: 0, y: 0, w: 1.5, h: 1.5)
gates.gate-nand(x: 3, y: 0, w: 1.5, h: 1.5, inverted: "all")
```

## Signature

```text
gate-nand(
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
| `<id>-port-out` | east | The output (already drawn with the bubble). |

## Pitfalls

- The output bubble is part of the gate's symbol — the port anchor still
  points at the rightmost tip, *not* the centre of the bubble.
- Setting `inverted: ("out",)` on a `gate-nand` *adds a second bubble*,
  which is rarely what you want. Use `gate-and` if you need an
  inverted-input NAND with no inverted output.

## Example

See [`examples/03-gate-nand/03-gate-nand.typ`](./examples/03-gate-nand/03-gate-nand.typ).

## Related

- [`02-gate-and.md`](./02-gate-and.md) — the non-inverted sibling.
- [`07-gate-nor.md`](./07-gate-nor.md) — the OR-side equivalent.
