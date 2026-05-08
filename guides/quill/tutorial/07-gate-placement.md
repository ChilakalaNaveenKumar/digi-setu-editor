# 7 — Gate placement (`x:` / `y:`)

By default, gates are placed automatically and sequentially. But every
gate, decoration, and group accepts optional `x:` (column) and `y:`
(row) parameters that pin it to a specific cell — similar to
`grid.cell` and `table.cell` in core Typst.

This is useful for:

- Removing repetition (place ten Hadamards in one expression with
  `range(...).map(...)`).
- Moving slice / gategroup definitions to the bottom of your source for
  readability while keeping their visual position correct.

## Placing many gates with `..range(n).map(...)`

```typst
#quantum-circuit(
  ..range(4).map(i => lstick($|0〉$, y: i, x: 0)),
  ..range(4).map(i => gate($H$, y: i, x: 1)),
  2,
  ctrl(2), 1, ctrl(1), 1, [\ ],
  3, ctrl(2), ctrl(), [\ ],
  2, ctrl(), [\ ],
  3, ctrl()
)
```

What happens:

- The first spread inserts four `lstick($|0〉$)` items, one per row at
  column 0.
- The second spread inserts four Hadamards at column 1.
- After the two spreads, the layout cursor sits at column 2 row 0 — the
  remaining items continue normally.

## Move groups / slices to the bottom

```typst
#quantum-circuit(
  1, $S^dagger$, $H$, ctrl(), $H$, $S$, 1, [\ ],
  3, ctrl(-1),
  gategroup(2, 5, x: 1, y: 0, stroke: purple,
    label: (pos: bottom, content: text(purple)[CY gate])),
  gategroup(2, 3, x: 2, y: 0, stroke: blue,
    label: text(blue)[CX gate]),
)
```

The two `gategroup(...)` items appear textually at the very end but
visually wrap their pinned `x` / `y` regions. The source stays readable
because the actual gate sequence is not interrupted by group syntax.

See [`examples/07-gate-placement/07-gate-placement.typ`](examples/07-gate-placement/07-gate-placement.typ).

## When `x` is set but `y: auto` (and vice versa)

- `x: int, y: auto` — pinned to that **column** on the *current* wire.
- `x: auto, y: int` — pinned to the *current column* on that **wire**;
  the column counter does **not** advance.

This is useful for stacking multiple things on the same column.

## Pitfalls

- A cell can hold only **one** gate. Placing a second gate at the same
  `(x, y)` is a runtime error.
- Manual placement does **not** create wires for empty cells — empty
  rows still need to be present (e.g. via `[\ ]` row breaks) so the
  layout knows how many wires there are.
- For `gategroup` with `x:` / `y:`, the positional `wires` and `steps`
  args become **sizes** (not endpoints).

## Next

[`08-styling.md`](08-styling.md) — `wire`, `color`, `fill`, `scale`.
