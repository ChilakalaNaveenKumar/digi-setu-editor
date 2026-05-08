# `swap()` — swap target (`×`)

The `×` swap symbol on a wire. Use two `swap()` calls (one with the
relative target offset, one without) to draw a SWAP gate.

## Signature

```typst
swap(
  ..n:        int,
  wire-count,
  size:       length = 7pt,
  label,
  wire-label: label-shape = none,
  wire-stroke: auto | stroke = auto,
  x, y,
)
```

## Variants

| Form | Effect |
| ---- | ------ |
| `swap(1)` | × symbol with control wire to the next wire down. |
| `swap()` | × symbol on the current wire (no control). |
| `swap(1, wire-label: $sigma$)` | × with a label on the control wire. |
| `swap(1, size: 10pt)` | Larger × glyph. |

A two-wire swap is **always two items**: `swap(1)` on the upper wire +
`swap()` on the lower wire (or `swap(-1)` if you start on the lower
wire and target the upper).

## Example

```typst
#quantum-circuit(
  1, swap(1), 1, [\ ],
  1, swap(),  1,
)
```

See [`examples/08-swap/08-swap.typ`](examples/08-swap/08-swap.typ).

## Pitfalls

- `swap()` alone is a half-swap — it doesn't link to anything.
- The control wire goes to the **relative** target (`swap(1)` →
  one wire down).
- `wire-label` lives on the *control* wire, not on the symbol; pass
  the full label dictionary to fine-tune position.

## Related

- Permutations: [`permute`](04-permute.md)
- Control dot: [`ctrl`](09-ctrl.md)
