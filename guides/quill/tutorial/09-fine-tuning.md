# 9 — Fine-tuning spacing with length items

`quantum-circuit(..)` accepts plain **length values** anywhere a gate
would go. They become *gutters* — extra space between two columns
(when placed mid-row) or between two wires (when placed after `[\\ ]`).

This is the per-cell version of `column-spacing` / `row-spacing` and is
the right tool for tightening / loosening just one part of a circuit.

## Horizontal gutter

Insert a length between two cells on the same row:

```typst
#quantum-circuit(
  $X$, $Y$, 10pt, $Z$
)
```

The 10pt is added to the gutter between the second and third columns.

If multiple length items target the **same column** on different rows,
the **maximum** is used. Likewise, several consecutive lengths
(e.g. `5pt, 10pt, 6pt`) collapse to the maximum.

## Vertical gutter

A length placed **after** `[\\ ]` becomes the vertical gutter
between the previous and next wire:

```typst
#quantum-circuit(
  $X$, [\ ], $Y$, [\ ], 10pt, $Z$
)
```

The 10pt is the extra vertical gap between the second and third wires.

See [`examples/09-fine-tuning/09-fine-tuning.typ`](examples/09-fine-tuning/09-fine-tuning.typ).

## When to reach for `min-row-height` / `min-column-width`

If you need a **minimum** size everywhere (because some rows are too
small to hold their lstick label), set the global `min-row-height` /
`min-column-width` on `quantum-circuit(..)`. Lengths between cells are
purely additive on top of the auto layout.

## Pitfalls

- A length without an adjacent gate has nothing to size against — it
  silently becomes 0. Always pair lengths with at least one gate per
  row.
- Vertical gutters affect **only** the gap immediately after the
  preceding `[\\ ]`. To add space at the top of the circuit, use
  `circuit-padding`.
- The "max wins" rule means 5pt + 10pt + 6pt is **10pt**, not 21pt.

## Next

[`10-annotations.md`](10-annotations.md) — `annotate(columns, rows,
callback)` for arbitrary overlays.
