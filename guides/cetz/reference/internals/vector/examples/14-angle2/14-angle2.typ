#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  let a = cetz.vector.angle2((0, 0), (1, 1))
  content((0, 0), [angle2((0,0), (1,1)) = #a])
})
