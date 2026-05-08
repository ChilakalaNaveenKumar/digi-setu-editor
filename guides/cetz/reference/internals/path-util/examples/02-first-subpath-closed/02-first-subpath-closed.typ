#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  let sp = cetz.path-util.make-subpath(
    (0, 0, 0),
    (("l", (1, 0, 0)),),
    closed: true,
  )
  let path = (sp,)
  content((0, 0), [first-closed? = #cetz.path-util.first-subpath-closed(path)])
})
