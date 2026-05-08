#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  let sp = cetz.path-util.make-subpath(
    (0, 0, 0),
    (("l", (1, 0, 0)), ("l", (1, 1, 0))),
    closed: true,
  )
  content((0,  0), [end (default) = #repr(cetz.path-util.subpath-end(sp))])
  content((0, -.5), [end (ignore close) = #repr(cetz.path-util.subpath-end(sp, ignore-close-flag: true))])
})
