#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  // A body can be `none`, an array of elements, or a function/closure.
  cetz.util.assert-body(none)
  cetz.util.assert-body(ctx => ())
  content((0, 0), [assert-body succeeded])
})
