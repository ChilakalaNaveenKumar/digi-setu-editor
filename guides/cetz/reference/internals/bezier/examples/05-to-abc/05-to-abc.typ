#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

// `to-abc` is consumed by `quadratic-through-3points` and
// `cubic-through-3points`. The user-visible effect is "draw a smooth
// curve from S to E through B" via `bezier-through`:
#cetz.canvas({
  import cetz.draw: *
  bezier-through((0, 0), (1.5, 1.5), (3, 0))
  circle((1.5, 1.5), radius: .07, fill: red)
})
