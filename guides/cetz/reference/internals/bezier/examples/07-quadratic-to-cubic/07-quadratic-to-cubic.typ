#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

// CeTZ's `bezier()` shape happens to accept either form (3 args =
// quadratic, 4 args = cubic). Internally a quadratic is promoted via
// `quadratic-to-cubic` before rendering.
#cetz.canvas({
  import cetz.draw: *
  bezier((0, 0), (3, 0), (1.5, 2))         // quadratic
  bezier((0, -1.5), (3, -1.5), (1, 0.3), (2, 0.3))  // cubic
})
