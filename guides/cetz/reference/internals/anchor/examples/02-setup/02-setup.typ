#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

// `anchor.setup` is invoked behind the scenes by every shape, including
// `group`. Using `anchor()` inside a `group(name: ...)` is the public
// way to drive it from user code.
#cetz.canvas({
  import cetz.draw: *
  group(name: "g", {
    circle((0, 0), radius: .4)
    anchor("tip", (0, .8))
  })
  line("g.tip", (1, 1.2), mark: (end: ">"))
})
