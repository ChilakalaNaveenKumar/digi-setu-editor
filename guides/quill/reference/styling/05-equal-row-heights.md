# `equal-row-heights` — uniform wire spacing

By default each row's height matches its tallest gate. With many small
gates and one tall one (e.g. multi-line label), wires end up unevenly
spaced. Set `equal-row-heights: true` to use the **largest row's
height** for every row.

```typst
#quantum-circuit(
  equal-row-heights: true,
  row-spacing: 2pt, min-row-height: 4pt,
  1, $H$, ctrl(1), $H$, 1, [\ ],
  1, $H$, targ(), $H$, 1, [\ ],
  2, ctrl(1), 2, [\ ],
  1, $H$, targ(), $H$, 1
)
```

See [`examples/05-equal-row-heights/05-equal-row-heights.typ`](examples/05-equal-row-heights/05-equal-row-heights.typ).

## Pitfalls

- Combine with a small `row-spacing` (`2-4pt`) so the equal heights
  don't waste vertical space.
- `equal-row-heights: true` does not affect column widths — pair with
  `min-column-width` for fully uniform grids.

## Related

- Spacing knobs: [`01-spacing.md`](01-spacing.md)
