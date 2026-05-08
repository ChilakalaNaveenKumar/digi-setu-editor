// Integration — Pinit (highlighting + arrows).
#import "@preview/touying:0.7.3": *
#import themes.simple: *
#import "@preview/pinit:0.2.2": *

#set text(size: 24pt)
#show: simple-theme.with(aspect-ratio: "16-9")

== Highlight + arrow
A simple #pin(1)highlighted text#pin(2).

#pinit-highlight(1, 2)
#pinit-point-from(2)[It is simple.]

== Multi-pin example
#slide[
  Insertion sort #pin("r1")example#pin("r2"):
  - Best case: $T(n) = O(n)$ #pin(3)
  - Worst case: $T(n) = O(n^2)$ #pin(4)
  #pinit-rect("r1", "r2")
  #pinit-place(3, dx: 15pt, dy: -15pt)[#text(red, weight: "bold")[Note]]
  #pinit-place(4, dx: 15pt, dy: -15pt)[#text(red, weight: "bold")[Slow!]]
]
