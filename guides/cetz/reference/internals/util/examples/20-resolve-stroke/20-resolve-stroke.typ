#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  content((0,  0), [resolve-stroke(2pt)              = #repr(cetz.util.resolve-stroke(2pt))])
  content((0, -.5), [resolve-stroke(red)              = #repr(cetz.util.resolve-stroke(red))])
  content((0, -1),  [resolve-stroke((paint: blue))    = #repr(cetz.util.resolve-stroke((paint: blue)))])
})
