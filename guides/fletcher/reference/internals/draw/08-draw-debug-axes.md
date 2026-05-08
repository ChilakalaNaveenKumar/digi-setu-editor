# `draw-debug-axes(grid, debug, floating)`

Draw the elastic-grid coordinate axes — the bluish ruler overlay you
see on a Fletcher diagram with `debug: 1` (or higher). This is the
piece that powers the `debug:` argument of `diagram(...)`.

## Signature

```typst
draw-debug-axes(
  grid:     dict,    // computed grid
  debug:    int,     // verbosity level (0 = off, 1 = axes, 2+ = more)
  floating: bool,    // draw on top (true) or behind (false) other content
)
```

## When to call manually

Inside a custom `render:` callback that bypasses
`fletcher.draw-diagram`. You still want the debug overlay during
development:

```typst
render: (grid, nodes, edges, options) => fletcher.cetz.canvas({
  // …your custom drawing…
  if options.debug > 0 {
    fletcher.draw-debug-axes(grid, options.debug, true)
  }
})
```

See [`examples/08-draw-debug-axes/08-draw-debug-axes.typ`](examples/08-draw-debug-axes/08-draw-debug-axes.typ).

## Pitfalls

- `floating: true` overlays the grid on top of the diagram —
  great for inspection, but unreadable when shipping.
- `debug: 0` makes this a no-op; check the level before calling so
  unsuspecting users don't always see the axes.

## Related

- `diagram(debug: …)` user-facing toggle.
- [`compute-grid`](../diagram/05-compute-grid.md) produces the dict
  this consumes.
