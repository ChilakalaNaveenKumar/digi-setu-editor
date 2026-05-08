// 'align(alignment, body)' aligns content along one or both axes.
//
// Single-axis: 'left', 'center', 'right'  (horizontal)
//              'top', 'horizon', 'bottom' (vertical)
// Two-axis  :  combine with '+'   ('right + bottom', 'center + horizon', ...)
//
// LOGICAL alignments 'start' / 'end' follow the text direction (LTR -> left/right).
//
// 'align' is BLOCK-LEVEL: it interrupts the current paragraph. To align
// pieces WITHIN the same line, use fractional 'h(1fr)' instead.

#set page(height: 200pt)

= Horizontal centering

#align(center)[
  Centered text, a sight to see \
  In perfect balance, visually
]

= Two-axis alignment

#align(right + bottom)[Right-bottom corner]

#pagebreak()

= Logical start/end (RTL flips them)

#stack(
  spacing: 6pt,
  align(start)[start (LTR -> left)],
  align(end)[end (LTR -> right)],
)

#set text(dir: rtl)
#align(start)[start (RTL -> right)]
#align(end)[end (RTL -> left)]
#set text(dir: ltr)

#pagebreak()

= Same-line alignment via fractional spacing

Start #h(1fr) Middle #h(1fr) End
