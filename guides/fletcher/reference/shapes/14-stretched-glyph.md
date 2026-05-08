# `stretched-glyph` — stretchable bracket / brace / arrow

Draws a *stretched glyph* (e.g. brace, bracket, paren, arrow) along
one side of a node. Especially useful with `enclose:` to wrap a group.

## Signature

```typst
stretched-glyph(
  node, extrude,
  glyph:     symbol | content = sym.brace.b,
  dir:       bottom,
  sep:       0pt,
  length:    100%,
  label:     none,
  label-sep: 0.25em,
  ..args:    any,
)
```

| Arg | Default | Effect |
| --- | ------- | ------ |
| `glyph` | `sym.brace.b` | Glyph to stretch — works best with stretchable glyphs. |
| `dir` | `bottom` | Side of the node to place the glyph on. |
| `sep` | `0pt` | Distance between glyph and node edge. |
| `length` | `100%` | Glyph size. `100% + 5pt` = 5pt longer than the node. |
| `label` | `none` | Content placed at the far side of the glyph. |
| `label-sep` | `0.25em` | Gap between label and glyph. |
| `..args` | — | Forwarded to `text(..)` (e.g. `fill: red`, `size: 3em`). |

## Example

```typst
#import fletcher.shapes: stretched-glyph

#diagram(
  node((0, 0), [NODE],
    shape: stretched-glyph.with(label: [label], dir: top)),
  node((1, 0), [NODE],
    shape: stretched-glyph.with(glyph: sym.bracket.b, label: [→ output])),
)
```

See [`examples/14-stretched-glyph/14-stretched-glyph.typ`](examples/14-stretched-glyph/14-stretched-glyph.typ).

## Pitfalls

- Match the glyph to the direction: `sym.brace.b` (bottom-stretch) is
  for `dir: bottom`. For top, use `sym.brace.t`.
- A non-stretchable glyph stays at its natural size — `length: 200%`
  becomes meaningless.
- `..args` go to **`text(..)`**, not `box(..)` — colour with `fill:`,
  not `text-fill:`.

## Related

- Brace wrapper: [`15-brace.md`](15-brace.md)
- Bracket wrapper: [`16-bracket.md`](16-bracket.md)
- Paren wrapper: [`17-paren.md`](17-paren.md)
