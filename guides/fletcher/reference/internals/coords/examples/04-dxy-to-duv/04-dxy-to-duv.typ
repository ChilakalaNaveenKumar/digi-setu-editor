// Internals/coords 04 — `dxy-to-duv` snaps a hand-positioned probe
// onto the elastic grid. We draw a state-machine and show that two
// equally-long *physical* nudges land at very different *elastic*
// positions because cell sizes differ.

#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
#set page(width: auto, height: auto, margin: 6pt)

#diagram(
  spacing: (16mm, 12mm),
  node-stroke: 0.6pt,
  node((0, 0), [start], shape: fletcher.shapes.pill),
  node((1, 0), [READING-LONG-LABEL], shape: fletcher.shapes.pill),
  node((2, 0), [done], shape: fletcher.shapes.pill),
  edge((0, 0), (1, 0), "->", $a$),
  edge((1, 0), (2, 0), "->", $b$),
  render: (grid, nodes, edges, options) => fletcher.cetz.canvas({
    fletcher.draw-diagram(grid, nodes, edges, debug: options.debug)
    for u in (0.4, 1.4) {
      let xy = fletcher.uv-to-xy(grid, (u, -0.7))
      let nudge = fletcher.dxy-to-duv(grid, xy, (8mm, 0pt))
      fletcher.cetz.draw.line(xy, (rel: (8mm, 0pt), to: xy),
        mark: (end: ">"), stroke: blue + 0.6pt)
      fletcher.cetz.draw.content(
        (rel: (4mm, 3mm), to: xy),
        text(7pt, blue)[#calc.round(nudge.at(0), digits: 2) uv]
      )
    }
  })
)
