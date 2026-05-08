// Gallery 02 — Pullback square with the right-angle marker.

#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
#set page(width: auto, height: auto, margin: 6pt)

#diagram(
  spacing: (22mm, 16mm),
  node-stroke: none,
  node((0, 0), $P$, name: <p>),
  node((1, 0), $X$, name: <x>),
  node((0, 1), $Y$, name: <y>),
  node((1, 1), $Z$, name: <z>),
  edge(<p>, <x>, "->", $p_X$),
  edge(<p>, <y>, "->", $p_Y$, label-side: right),
  edge(<x>, <z>, "->", $f$),
  edge(<y>, <z>, "->", $g$, label-side: right),
  render: (grid, nodes, edges, options) => fletcher.cetz.canvas({
    fletcher.draw-diagram(grid, nodes, edges, debug: options.debug)
    let p = fletcher.uv-to-xy(grid, (0, 0))
    let r = 4mm
    fletcher.cetz.draw.line(
      (p.at(0) + r,    p.at(1) - r/2),
      (p.at(0) + r,    p.at(1) - 3*r/2),
      (p.at(0),        p.at(1) - 3*r/2),
      stroke: 0.6pt,
    )
  })
)
