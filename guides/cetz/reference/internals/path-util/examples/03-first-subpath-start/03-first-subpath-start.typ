#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  let sp = cetz.path-util.make-subpath(
    (1, 2, 0),
    (("l", (3, 4, 0)),),
  )
  let p = cetz.path-util.first-subpath-start((sp,))
  content((0, 0), [first start = #repr(p)])
})
