#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  let d = cetz.vector.dist((0, 0, 0), (3, 4, 0))
  content((0, 0), [dist = #d])
})
