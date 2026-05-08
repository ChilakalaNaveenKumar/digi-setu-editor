#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  arc((0, 0),  start: 45deg, stop: 135deg)
  arc((2, 0),  start: 45deg, delta: 90deg, mode: "CLOSE")
  arc((4, 0),  stop: 135deg, delta: 90deg, mode: "PIE")
})
