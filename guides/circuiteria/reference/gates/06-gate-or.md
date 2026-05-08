# `gates.gate-or()` — OR Gate

Draws an OR gate (curved-back shape with pointed output). Also available
as `element.gate-or()`.

```text
gates.gate-or(x: 0, y: 0, w: 1.5, h: 1.5)
gates.gate-or(x: 3, y: 0, w: 1.5, h: 1.5, inverted: "all")
```

## Signature

```text
gate-or(
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

- The OR gate's curved back means the input ports are *not* on a flat
  vertical line — but the anchors are still placed at the same x for
  every input, so wiring lines come in straight.

## Example

See [`examples/06-gate-or/06-gate-or.typ`](./examples/06-gate-or/06-gate-or.typ).

## Related

- [`07-gate-nor.md`](./07-gate-nor.md) — the inverted-output sibling.
- [`08-gate-xor.md`](./08-gate-xor.md) — XOR adds an extra back-curve.
