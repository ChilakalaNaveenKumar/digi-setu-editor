# `nwire()` — wire bundle marker

Annotates a wire to be a *bundle of n quantum or classical wires*. The
visual is similar to the `\qwbundle` command in `quantikz` — a small
slash + label sitting on the wire.

## Signature

```typst
nwire(
  body: int | content,
  x, y,
)
```

`body` is the label placed on top of the slash. Pass an integer (e.g.
`5`) for "5 wires"; pass arbitrary content (e.g. `nwire([])` or
`nwire("")`) for an unlabelled slash.

## Example

```typst
#quantum-circuit(
  1, nwire($5$), 1
)
```

See [`examples/04-nwire/04-nwire.typ`](examples/04-nwire/04-nwire.typ).

## Pitfalls

- `nwire` is *purely visual* — Typst still treats it as a single wire
  for layout. To actually draw multiple parallel lines, use
  [`setwire(n, wire-distance: ...)`](05-setwire.md).
- The label sits *above* the wire by default; the cell width is the
  natural width of the slash + label.

## Related

- Multiple physical wires: [`setwire`](05-setwire.md)
- Permutations across many wires: [`permute`](../gates/04-permute.md)
