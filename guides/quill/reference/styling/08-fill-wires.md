# `fill-wires` — auto-extend wires to the right edge

By default, every wire is automatically padded with extra wire on its
right end so all wires line up at the same right boundary. Set
`fill-wires: false` to **disable** this and let each wire end at its
last gate.

## Examples

```typst
// Default: every wire extends to the same right edge.
#quantum-circuit(
  1, $H$, ctrl(1), 1, [\ ],
  1, 1, targ(),
)

// fill-wires: false — wires end at the last gate.
#quantum-circuit(
  fill-wires: false,
  1, $H$, ctrl(1), 1, [\ ],
  1, 1, targ(),
)
```

See [`examples/08-fill-wires/08-fill-wires.typ`](examples/08-fill-wires/08-fill-wires.typ).

## Pitfalls

- The Nielsen-Chuang demos in [`demos/`](../../demos/) often need
  `fill-wires: false` so the last column doesn't have a trailing wire
  past `meter()`.
- With `fill-wires: false`, the bounding box becomes
  *ragged* — combine with `circuit-padding` to keep alignment in
  surrounding text.

## Related

- Wire styling: [`setwire`](../decorations/05-setwire.md)
- Explicit layout: [`07-wires-explicit.md`](07-wires-explicit.md)
