// Internals/diagram 05 — drop ruler tick marks at every grid position
// using the `grid.centers` arrays produced by `compute-grid`. Genuinely
// useful when debugging custom shapes.

#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
#set page(width: auto, height: auto, margin: 6pt)

#diagram(
  spacing: (16mm, 12mm),
  node-stroke: 0.5pt,
  node((0, 0), $A$, name: <a>),
  node((2, 0), $B$, name: <b>),
  node((1, 1), $C$, name: <c>),
  edge(<a>, <b>, "->", $f$),
  edge(<a>, <c>, "->", $g$, label-side: right),
  edge(<c>, <b>, "->", $h$),
  render: (grid, nodes, edges, options) => fletcher.cetz.canvas({
    fletcher.draw-diagram(grid, nodes, edges, debug: options.debug)
    let xs = grid.centers.at(0)
    let ys = grid.centers.at(1)
    let y-bottom = ys.last() + 6mm
    let x-left = xs.first() - 8mm
    for (i, x) in xs.enumerate() {
      fletcher.cetz.draw.line((x, y-bottom - 1mm), (x, y-bottom),
        stroke: 0.4pt + red)
      fletcher.cetz.draw.content((x, y-bottom + 2mm),
        text(7pt, red)[#i])
    }
    for (j, y) in ys.enumerate() {
      fletcher.cetz.draw.line((x-left + 1mm, y), (x-left, y),
        stroke: 0.4pt + red)
      fletcher.cetz.draw.content((x-left - 2mm, y),
        text(7pt, red)[#j])
    }
  })
)
