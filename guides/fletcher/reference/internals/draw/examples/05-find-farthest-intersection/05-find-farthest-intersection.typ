// Internals/draw 05 — visualise where an external line *enters* a
// thick node by placing markers on the outline. Uses get-node-anchor
// (angle-based form) which is the public-friendly counterpart of
// find-farthest-intersection.

#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
#set page(width: auto, height: auto, margin: 6pt)

#diagram(
  spacing: (24mm, 14mm),
  node((0, 0), [Source], shape: fletcher.shapes.diamond,
    fill: orange.lighten(80%), name: <s>),
  node((1, 0), [], width: 30mm, height: 18mm,
    shape: fletcher.shapes.rect, stroke: 0.6pt, name: <t>),
  edge(<s>, <t>, "->"),
  render: (grid, nodes, edges, options) => fletcher.cetz.canvas({
    fletcher.draw-diagram(grid, nodes, edges, debug: options.debug)
    let target = fletcher.find-node-at(nodes, (1, 0))
    fletcher.get-node-anchor(target, 180deg, p => {
      fletcher.cetz.draw.circle(p, radius: 1.5pt, fill: red)
    })
    fletcher.get-node-anchor(target, 90deg, p => {
      fletcher.cetz.draw.circle(p, radius: 1.5pt, fill: blue)
    })
  })
)
