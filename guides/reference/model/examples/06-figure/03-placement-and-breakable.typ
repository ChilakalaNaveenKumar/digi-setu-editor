// 'placement' makes the figure FLOAT to the top or bottom of the page.
//   none    in-flow exactly where written (default)
//   auto    nearest of top/bottom
//   top     float to top
//   bottom  float to bottom
//
// 'scope' controls which container the placement is relative to.
//   "column"  current column (default)
//   "parent"  full-width across columns (useful in multi-column layouts)
//
// To make the figure ITSELF breakable across pages (e.g. when it contains
// a long table), apply this show rule:
//   #show figure: set block(breakable: true)
//
// The clearance between floating content and the main flow is set on 'place':
//   #show figure: set place(clearance: 1em)

#set page(height: 220pt)
#show figure: set place(clearance: 1em)

= Introduction

#figure(
  placement: bottom,
  caption: [A caption-bearing figure that floats to the bottom.],
  rect(width: 100%, height: 50pt, fill: orange.lighten(70%))[Floating block],
)

#lorem(80)
