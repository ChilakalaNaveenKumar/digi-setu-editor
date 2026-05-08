// 'page' configures the page itself. Almost always used as 'set page(...)'.
//
// Most-used fields:
//   paper        str (e.g. "us-letter", "a4")    shorthand for width+height
//   width / height                                explicit; either may be 'auto'
//   flipped      bool                             rotate to landscape
//   margin       relative | dictionary            per-side dictionary supported
//   binding      auto | left | right              affects 'inside'/'outside' margins
//   columns      int                              page-level columns
//   fill         color | gradient | tiling        background color
//   numbering    none | str | function            page numbers
//   number-align alignment                         (top/bottom; never horizon)
//   header / footer / background / foreground     content slots

#set page(
  paper: "a5",
  margin: (x: 1.5cm, y: 1cm),
  numbering: "1 / 1",
  number-align: right + bottom,
  header: [_Typst Agent_ #h(1fr) Layout module],
)

= Page basics

This page uses A5 paper, 1.5cm horizontal and 1cm vertical margins, a
right-bottom page number "X / N", and a custom header that includes the
filler "h(1fr)" trick to push "Layout module" to the right edge.

#lorem(40)

#pagebreak()

= Background watermark

#set page(background: rotate(24deg,
  text(36pt, fill: rgb("FFCBC4"))[CONFIDENTIAL]
))

#set page(background: none)
After this set rule the next page no longer has the watermark, but THIS
page does because the previous set was scoped above.

#lorem(40)
