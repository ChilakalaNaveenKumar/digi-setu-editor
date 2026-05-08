#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  set-style(nstar: (radius: 0.65))
  n-star((0, 0), 5)
  // 8-pointed star, rotated
  n-star((1.5, 0), 8, angle: 11.25deg)
  // 6-pointed star showing its inner hexagon
  n-star((3, 0), 6, show-inner: true)
})
