#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  line((0, 0), (60deg, 2),  name: "a")
  line((0, 0), (330deg, 2), name: "b")
  cetz.angle.angle(
    "a.start", "a.end", "b.end",
    label: $alpha$,
    mark: (end: ">"),
    radius: 1.5,
  )
  cetz.angle.angle(
    "a.start", "b.end", "a.end",
    label: $beta$,
    radius: 50%,
    direction: "ccw",
  )
})
