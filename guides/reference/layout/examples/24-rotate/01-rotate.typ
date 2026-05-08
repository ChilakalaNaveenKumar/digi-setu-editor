// 'rotate(angle, origin: center + horizon, reflow: false, body)' rotates
// content. By default the LAYOUT acts as if the content was NOT rotated
// (its bounding box stays the same). 'reflow: true' adjusts the layout
// to the new rotated bounding box.

= Sweep through angles in a stack

#stack(
  dir: ltr,
  spacing: 1fr,
  ..range(8).map(i => box(rotate(45deg * i)[X])),
)

= Origin alignment

#set text(spacing: 8pt)
#let sq = square.with(width: 8pt, fill: aqua)

#box(sq())
#box(rotate(30deg, origin: center, sq()))
#box(rotate(30deg, origin: top + left, sq()))
#box(rotate(30deg, origin: bottom + right, sq()))

= reflow: false (default) -- rotated content overlaps siblings

A #rotate(45deg)[B] C \
A #rotate(90deg)[B] C

= reflow: true -- bounding box adjusts

A #rotate(45deg, reflow: true)[B] C \
A #rotate(90deg, reflow: true)[B] C

= Radians work too

#rotate(-1.571rad)[Space!]
