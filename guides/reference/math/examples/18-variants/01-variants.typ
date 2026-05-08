// Math TYPEFACE variants. These are alternate letterforms encoded in the
// math font (NOT the same as switching the regular text font!).
//
//   serif(body)   roman (default)
//   sans(body)    sans-serif
//   frak(body)    fraktur
//   mono(body)    monospace
//   bb(body)      blackboard bold (double-struck)
//   cal(body)     calligraphic (chancery)
//   scr(body)     script (roundhand)

= Side-by-side comparison

$ A B C quad
  serif(A B C) quad
  sans(A B C) quad
  frak(P Q R) quad
  mono(x + y) $

= Blackboard bold (number sets)

$ bb(N) = NN quad bb(R) = RR quad bb(C) = CC $

$ f : NN -> RR $

= Calligraphic vs script

Let $cal(P)$ be the set of all paths.

The script alternative $scr(L)$ is not the same as the linear-maps set $cal(L)$,
when the font supports both via Unicode variation sequences.

= Defining 'scr' via stylistic set (font-feature workaround)

When 'scr' produces the same glyph as 'cal' (because the font lacks the
variation sequence), you can build it from a stylistic set instead:

#let myscr(it) = text(stylistic-set: 1, $cal(it)$)

We establish $cal(P) != myscr(P)$.
