#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  let path = (
    cetz.path-util.make-subpath(
      (0, 0, 0),
      (("l", (3, 0, 0)), ("l", (3, 4, 0))),
    ),
  )
  content((0, 0), [length = #cetz.path-util.length(path)])
})
