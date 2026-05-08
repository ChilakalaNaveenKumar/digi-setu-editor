#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  let p = cetz.util.line-pt((0, 0, 0), (4, 2, 0), 0.25)
  content((0, 0), [line-pt(t=0.25) = #repr(p)])
})
