#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  line((0, 0), (1, 2),  name: "a")
  line((0, 0), (2, -1), name: "b")
  cetz.angle.right-angle(
    "a.start", "a.end", "b.end",
    radius: 1.5,
  )
})
