# `gates.gate-xor()` — XOR Gate

Draws an XOR gate (the OR shape with an extra back-curve, denoting
exclusive-or). Also available as `element.gate-xor()`.

```text
gates.gate-xor(x: 0, y: 0, w: 1.5, h: 1.5)
gates.gate-xor(x: 3, y: 0, w: 1.5, h: 1.5, inverted: "all")
```

## Signature

```text
gate-xor(
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
| `<id>-port-out` | east | The output. |

## Pitfalls

- "XOR with more than two inputs" is a contested concept in logic. The
  symbol still renders, but interpret it carefully.
- The extra back-curve sits *outside* the gate's bounding box on the
  west side — leave a little margin when placing other elements
  immediately to the left.

## Example

See [`examples/08-gate-xor/08-gate-xor.typ`](./examples/08-gate-xor/08-gate-xor.typ).

## Related

- [`09-gate-xnor.md`](./09-gate-xnor.md) — the inverted-output sibling.
- [`06-gate-or.md`](./06-gate-or.md) — the non-exclusive variant.
