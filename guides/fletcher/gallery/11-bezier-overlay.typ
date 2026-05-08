// Gallery 11 — Edges drawn as Bezier curves via the `render:` callback
// + CeTZ. Useful when Fletcher's stock arc isn't expressive enough.

#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
#set page(width: auto, height: auto, margin: 6pt)

#diagram(
  spacing: (24mm, 18mm),
  node-stroke: 0.6pt,
  node((0, 0), [Source], shape: fletcher.shapes.diamond,
    fill: orange.lighten(80%), name: <s>),
  node((2, 0), [Sink], shape: fletcher.shapes.pill,
    fill: green.lighten(80%), name: <t>),
  edge(<s>, <t>, "->", $f$),
  render: (grid, nodes, edges, options) => fletcher.cetz.canvas({
    fletcher.draw-diagram(grid, nodes, edges, debug: options.debug)
    let n1 = fletcher.find-node-at(nodes, (0, 0))
    let n2 = fletcher.find-node-at(nodes, (2, 0))
    let theta-out = 90deg
    let theta-in = -90deg
    fletcher.get-node-anchor(n1, theta-out, p1 => {
      fletcher.get-node-anchor(n2, theta-in, p2 => {
        let c1 = (rel: (theta-out, 22mm), to: p1)
        let c2 = (rel: (theta-in, 22mm), to: p2)
        fletcher.cetz.draw.bezier(p1, p2, c1, c2,
          mark: (end: ">"),
          stroke: 0.7pt + purple)
        fletcher.cetz.draw.content(
          (rel: (0pt, -10mm),
           to: ((p1.at(0) + p2.at(0))/2, (p1.at(1) + p2.at(1))/2)),
          text(8pt, purple)[Bezier loop],
        )
      })
    })
  }),
)
