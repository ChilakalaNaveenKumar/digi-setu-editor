# `paren` — stretched parenthesis

Convenience wrapper around `stretched-glyph` with `glyph: sym.paren.b`.

## Example

```typst
#import fletcher.shapes: paren

#diagram(
  spacing: 1cm,
  node-stroke: teal,
  node((0, 0), $A$, name: <A>),
  node((1, 0), $B$, name: <B>),
  node(enclose: (<A>, <B>),
    shape: paren.with(dir: top, label: [tuple])),
)
```

See [`examples/17-paren/17-paren.typ`](examples/17-paren/17-paren.typ).

## Pitfalls

- Parens stretch *vertically* better than bracket / brace; for very
  short groups they may end up shorter than the brace would.

## Related

- Underlying primitive: [`stretched-glyph`](14-stretched-glyph.md)
