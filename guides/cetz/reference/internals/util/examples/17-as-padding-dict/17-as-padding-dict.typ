#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  content((0,  0), [pad(0.5)        = #repr(cetz.util.as-padding-dict(0.5))])
  content((0, -.5), [pad((1, 2))     = #repr(cetz.util.as-padding-dict((1, 2)))])
  content((0, -1),  [pad((1, 2, 3, 4)) = #repr(cetz.util.as-padding-dict((1, 2, 3, 4)))])
})
