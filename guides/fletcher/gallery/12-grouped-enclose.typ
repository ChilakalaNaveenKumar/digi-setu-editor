// Gallery 12 — Grouped sub-systems with `enclose:` (an OS architecture).

#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
#set page(width: auto, height: auto, margin: 6pt)

#let app(uv, lbl) = fletcher.node(uv, lbl,
  shape: fletcher.shapes.rect, fill: blue.lighten(85%),
  stroke: 0.5pt, inset: 4pt, name: label("a-" + str(uv.at(0)) + "-" + str(uv.at(1))))

#let svc(uv, lbl) = fletcher.node(uv, lbl,
  shape: fletcher.shapes.rect, fill: orange.lighten(80%),
  stroke: 0.5pt, inset: 4pt, name: label("s-" + str(uv.at(0)) + "-" + str(uv.at(1))))

#let drv(uv, lbl) = fletcher.node(uv, lbl,
  shape: fletcher.shapes.rect, fill: green.lighten(85%),
  stroke: 0.5pt, inset: 4pt, name: label("d-" + str(uv.at(0)) + "-" + str(uv.at(1))))

#diagram(
  spacing: (8mm, 12mm),
  app((0, 0), [editor]),
  app((1, 0), [browser]),
  app((2, 0), [shell]),
  svc((0, 1), [vfs]),
  svc((1, 1), [net]),
  svc((2, 1), [audio]),
  drv((0, 2), [block-dev]),
  drv((1, 2), [nic]),
  drv((2, 2), [pcm]),
  edge(<a-0-0>, <s-0-1>, "->"),
  edge(<a-1-0>, <s-1-1>, "->"),
  edge(<a-2-0>, <s-0-1>, "->"),
  edge(<s-0-1>, <d-0-2>, "->"),
  edge(<s-1-1>, <d-1-2>, "->"),
  edge(<s-2-1>, <d-2-2>, "->"),
  node(enclose: (<a-0-0>, <a-1-0>, <a-2-0>),
    inset: 6pt, stroke: (paint: blue, dash: "dashed"),
    label: text(7pt, blue.darken(20%))[applications]),
  node(enclose: (<s-0-1>, <s-1-1>, <s-2-1>),
    inset: 6pt, stroke: (paint: orange.darken(10%), dash: "dashed"),
    label: text(7pt, orange.darken(30%))[kernel services]),
  node(enclose: (<d-0-2>, <d-1-2>, <d-2-2>),
    inset: 6pt, stroke: (paint: green.darken(20%), dash: "dashed"),
    label: text(7pt, green.darken(30%))[device drivers]),
)
