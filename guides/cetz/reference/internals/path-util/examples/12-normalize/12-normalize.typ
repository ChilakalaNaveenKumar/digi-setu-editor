#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  let raw = (
    cetz.path-util.make-subpath(
      (0, 0, 0),
      (("l", (1, 0, 0)),),
    ),
  )
  let normalized = cetz.path-util.normalize(raw)
  content((0, 0), [normalized count = #normalized.len()])
})
