// COMPILE WITH:  typst compile --features html 01-target-branching.typ
//
// 'target()' is a CONTEXTUAL function (must be inside a 'context { ... }'
// block). It returns:
//   "paged"  for PDF, PNG, SVG export
//   "html"   for HTML export
//
// It is currently behind the 'html' experimental feature flag. The API
// shape is not yet finalized; expect minor changes in future versions.
//
// IMPORTANT: inside an 'html.frame' (used to embed paged content inside an
// HTML document) target() returns "paged" even when exporting HTML. So the
// target reflects the ACTIVE rendering context, not the top-level export
// format. Use it in templates / show rules; avoid baking it into content.

#let kbd(it) = context {
  if target() == "html" {
    html.elem("kbd", it)
  } else {
    set text(fill: rgb("#1f2328"))
    let r = 3pt
    box(
      fill: rgb("#f6f8fa"),
      stroke: rgb("#d1d9e0b3"),
      outset: (y: r),
      inset: (x: r),
      radius: r,
      raw(it),
    )
  }
}

Press #kbd("F1") for help; this file was compiled to #context target().
