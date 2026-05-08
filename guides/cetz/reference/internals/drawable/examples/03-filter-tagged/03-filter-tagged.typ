#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  let a = cetz.drawable.apply-tags(
    cetz.drawable.line-strip(((0, 0, 0), (1, 0, 0))),
    "axis",
  )
  let b = cetz.drawable.apply-tags(
    cetz.drawable.line-strip(((0, 0, 0), (0, 1, 0))),
    "tick",
  )
  // Drop everything tagged "axis"; we should be left with just `b`.
  let kept = cetz.drawable.filter-tagged((a, b), "axis")
  content((0, 0), [remaining = #kept.len()])
})
