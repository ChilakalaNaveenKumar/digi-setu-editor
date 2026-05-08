// Internals/coords 02 — `xy-to-uv` gives you back the elastic position
// of a hand-placed CeTZ shape. Here we have a real DFA: from a hard-
// coded `(2.4cm, 0pt)` annotation we recover its (uv) cell and label it.

#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
#set page(width: auto, height: auto, margin: 6pt)

#diagram(
  spacing: (16mm, 12mm),
  node-stroke: 0.6pt,
  node((0, 0), $q_0$, shape: fletcher.shapes.circle),
  node((1, 0), $q_1$, shape: fletcher.shapes.circle),
  node((2, 0), $q_2$, shape: fletcher.shapes.circle),
  edge((-0.5, 0), (0, 0), "->"),
  edge((0, 0), (1, 0), "->", $a$),
  edge((1, 0), (2, 0), "->", $b$),
  edge((2, 0), (0, 0), "->", $c$, bend: -40deg),
  render: (grid, nodes, edges, options) => fletcher.cetz.canvas({
    fletcher.draw-diagram(grid, nodes, edges, debug: options.debug)
    let target-xy = (2.4cm, -8mm)
    fletcher.cetz.draw.circle(target-xy, radius: 1.5pt, fill: red)
    let uv = fletcher.xy-to-uv(grid, target-xy)
    fletcher.cetz.draw.content(
      (rel: (0pt, -3mm), to: target-xy),
      align(center)[uv $approx$ \
        (#calc.round(uv.at(0), digits: 2), #calc.round(uv.at(1), digits: 2))],
    )
  })
)
