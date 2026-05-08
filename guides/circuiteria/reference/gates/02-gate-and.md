# `gates.gate-and()` — AND Gate

Draws an AND gate (the classic D-shape symbol). Also available as
`element.gate-and()`.

```text
gates.gate-and(x: 0, y: 0, w: 1.5, h: 1.5)
gates.gate-and(x: 3, y: 0, w: 1.5, h: 1.5, inverted: "all")
```

## Signature

```text
gate-and(
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

- `inverted: "all"` adds the bubble to *all* ports including the output —
  visually similar to a NAND-with-inverted-inputs (an OR by De Morgan).
- For the standard NAND symbol (D-shape with one bubble on the output),
  use [`gate-nand`](./03-gate-nand.md) directly.

## Example

See [`examples/02-gate-and/02-gate-and.typ`](./examples/02-gate-and/02-gate-and.typ).

## Related

- [`03-gate-nand.md`](./03-gate-nand.md) — the inverted-output sibling.
- [`06-gate-or.md`](./06-gate-or.md) — the dual.
