// Shapes 14 — stretched-glyph.
#import "@preview/fletcher:0.5.8" as fletcher: diagram, node
#import fletcher.shapes: stretched-glyph
#set page(width: auto, height: auto, margin: 6pt)

#diagram(
  node((0, 0), [NODE],
    shape: stretched-glyph.with(label: [label], dir: top)),
  node((1, 0), [NODE],
    shape: stretched-glyph.with(glyph: sym.bracket.b, label: [→ output])),
)
