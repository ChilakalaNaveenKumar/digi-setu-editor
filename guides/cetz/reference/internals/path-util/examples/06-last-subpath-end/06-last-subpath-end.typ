#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  let path = (
    cetz.path-util.make-subpath((0, 0, 0), (("l", (1, 0, 0)),)),
    cetz.path-util.make-subpath((2, 0, 0), (("l", (3, 1, 0)),)),
  )
  content((0, 0), [last end = #repr(cetz.path-util.last-subpath-end(path))])
})
