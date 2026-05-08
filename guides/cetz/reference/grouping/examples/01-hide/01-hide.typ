#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  set-style(radius: .5)
  intersections("i", {
    circle((0, 0), name: "a")
    circle((1, 2), name: "b")
    // Use a hidden line to find the border intersections
    hide(line("a.center", "b.center"))
  })
  line("i.0", "i.1")
})
