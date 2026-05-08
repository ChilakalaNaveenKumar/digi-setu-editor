#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

#cetz.canvas({
  import cetz.draw: *
  let d = cetz.drawable.line-strip(((0, 0, 0), (1, 1, 0)))
  let tagged = cetz.drawable.apply-tags(d, "annotation")
  // apply-tags accepts a single drawable or an array; here we passed one
  // drawable, so we get one back with `tags` populated.
  content((0, 0), [tags = #repr(tagged.tags)])
})
