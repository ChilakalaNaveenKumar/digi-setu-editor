#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  // Label nodes anchors
  rect((0, 0), (2, 2), name: "my-rect")
  for-each-anchor(
    "my-rect",
    exclude: ("start", "mid", "end"),
    (name) => {
      content((), box(inset: 1pt, fill: white, text(8pt, [#name])),
              angle: -30deg)
    },
  )
})
