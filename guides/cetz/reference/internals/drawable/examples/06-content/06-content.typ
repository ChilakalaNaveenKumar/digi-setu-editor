#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  // The content() shape (in cetz.draw) ultimately produces a
  // drawable.content() under the hood. Drawing it the normal way is the
  // safest way to demonstrate the rendering side of this drawable kind.
  content((0, 0), [drawable.content holds a body])
})
