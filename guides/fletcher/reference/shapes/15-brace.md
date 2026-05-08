# `brace` — stretched curly brace

Convenience wrapper around `stretched-glyph` with `glyph: sym.brace.b`.

## Signature

Inherits from `stretched-glyph(...)` — same arguments minus `glyph`,
which is fixed to `sym.brace.b`.

## Example

```typst
#import fletcher.shapes: brace

#diagram(
  spacing: 1cm,
  node-stroke: teal,
  node((0, 0), $A$, name: <A>),
  node((1, 0), $B$, name: <B>),
  node(enclose: (<A>, <B>), shape: brace.with(dir: top, label: [pair])),
)
```

See [`examples/15-brace/15-brace.typ`](examples/15-brace/15-brace.typ).

## Pitfalls

- Use `dir: top` for an upward-opening brace (which uses `sym.brace.t`
  internally — Fletcher picks the right glyph based on `dir`).
- For a custom-coloured brace, pass `fill: red` etc. — those go to
  the `text(..)` element wrapping the glyph.

## Related

- Underlying primitive: [`stretched-glyph`](14-stretched-glyph.md)
- Bracket variant: [`bracket`](16-bracket.md)
- Paren variant: [`paren`](17-paren.md)
