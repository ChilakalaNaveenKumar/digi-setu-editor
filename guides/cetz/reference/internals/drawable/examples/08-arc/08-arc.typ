#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  let d = cetz.drawable.arc(0, 0, 0, 0deg, 90deg, 1, 1, mode: "PIE")
  content((0, 1.5), [#d.len() drawable(s)])
  // Equivalent shape:
  arc((0, 0), start: 0deg, stop: 90deg, radius: 1, mode: "PIE")
})
