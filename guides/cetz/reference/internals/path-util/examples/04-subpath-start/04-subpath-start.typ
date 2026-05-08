#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  let sp = cetz.path-util.make-subpath(
    (1, 2, 0),
    (("l", (3, 4, 0)),),
  )
  content((0, 0), [start = #repr(cetz.path-util.subpath-start(sp))])
})
