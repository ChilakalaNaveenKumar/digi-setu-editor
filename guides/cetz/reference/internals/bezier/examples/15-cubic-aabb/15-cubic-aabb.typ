#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

// The cetz canvas debug option shows the tight AABB that comes from
// `cubic-aabb`.
#cetz.canvas(debug: true, {
  import cetz.draw: *
  bezier((0, 0), (4, 0), (1, 2), (3, -2))
})
