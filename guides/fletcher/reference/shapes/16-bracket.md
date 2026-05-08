# `bracket` — stretched square bracket

Convenience wrapper around `stretched-glyph` with `glyph: sym.bracket.b`.

## Example

```typst
#import fletcher.shapes: bracket

#diagram(
  spacing: 1cm,
  node-stroke: teal,
  node((0, 0), $A$, name: <A>),
  node((1, 0), $B$, name: <B>),
  node(enclose: (<A>, <B>),
    shape: bracket.with(dir: top, size: 2em)),
)
```

See [`examples/16-bracket/16-bracket.typ`](examples/16-bracket/16-bracket.typ).

## Pitfalls

- Brackets in Typst's default font are *less* stretchable than braces;
  for very long groups they may visually plateau.
- Pair `dir: top` with `sym.bracket.t` if you customise the glyph.

## Related

- Underlying primitive: [`stretched-glyph`](14-stretched-glyph.md)
