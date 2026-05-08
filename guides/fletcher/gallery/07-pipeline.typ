// Gallery 07 — CI/CD pipeline with branches and a feedback loop.

#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
#set page(width: auto, height: auto, margin: 6pt)

#let stage(uv, lbl, fill) = fletcher.node(uv, align(center, lbl),
  shape: fletcher.shapes.pill, fill: fill, stroke: 0.5pt, inset: 5pt)

#diagram(
  spacing: (16mm, 12mm),
  stage((0, 1), [Source\ commit], blue.lighten(85%)),
  stage((1, 1), [Lint], yellow.lighten(75%)),
  stage((2, 1), [Unit\ tests], yellow.lighten(75%)),
  stage((3, 0), [Build\ Linux], orange.lighten(80%)),
  stage((3, 1), [Build\ macOS], orange.lighten(80%)),
  stage((3, 2), [Build\ Windows], orange.lighten(80%)),
  stage((4, 1), [Integration\ tests], red.lighten(80%)),
  stage((5, 1), [Deploy], green.lighten(80%)),
  edge((0, 1), (1, 1), "->"),
  edge((1, 1), (2, 1), "->"),
  edge((2, 1), (3, 0), "->"),
  edge((2, 1), (3, 1), "->"),
  edge((2, 1), (3, 2), "->"),
  edge((3, 0), (4, 1), "->"),
  edge((3, 1), (4, 1), "->"),
  edge((3, 2), (4, 1), "->"),
  edge((4, 1), (5, 1), "->", $"green"$),
  edge((4, 1), (0, 1), "..>", $"red ⇒ revert"$, bend: -45deg,
    label-pos: 0.4),
)
