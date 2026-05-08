// Internals/diagram 02 — sequence-diagram-style protocol with
// fractional positions, which exercises `expand-fractional-rects`.
// Half-row positions land cleanly between the integer rows so we can
// drop "in flight" message boxes between participants.

#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
#set page(width: auto, height: auto, margin: 6pt)

#diagram(
  spacing: (24mm, 9mm),
  node-stroke: 0.5pt,
  node((0, 0), [Alice], shape: fletcher.shapes.pill),
  node((1, 0), [Bob], shape: fletcher.shapes.pill),
  node((0.5, 1), [SYN], fill: yellow.lighten(70%)),
  node((0.5, 2), [SYN-ACK], fill: yellow.lighten(70%)),
  node((0.5, 3), [ACK], fill: yellow.lighten(70%)),
  node((0, 4), [Alice], shape: fletcher.shapes.pill),
  node((1, 4), [Bob], shape: fletcher.shapes.pill),
  edge((0, 0), (0.5, 1), "->"),
  edge((0.5, 1), (1, 0), "->"),
  edge((1, 0), (0.5, 2), "->"),
  edge((0.5, 2), (0, 0), "->"),
  edge((0, 0), (0.5, 3), "->"),
  edge((0.5, 3), (1, 4), "->"),
)
