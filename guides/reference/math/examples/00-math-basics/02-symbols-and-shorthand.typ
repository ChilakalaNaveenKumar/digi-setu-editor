// SYMBOLS available in math mode (no 'sym.' prefix needed):
//   pi, dot, RR, NN, ZZ, QQ, CC, oo (infinity), partial, integral, sum, ...
//   Greek by name: alpha, beta, gamma, ..., omega, Alpha, Beta, ...
//   Modifiers via dot syntax: arrow.r, arrow.l.r, gt.eq.not, ...
//
// SHORTHANDS recognised by Typst:
//   ->        arrow.r
//   <-        arrow.l
//   <->       arrow.l.r
//   =>        arrow.r.double
//   <=>       arrow.l.r.double
//   |->       arrow.r.bar
//   |>        triangle.r.small  / triangle.stroked.r (varies)
//   ::=       def equal
//   :=        colon.eq
//   != / <= / >=  not equal, leq, geq

$ x < y => x gt.eq.not y $

$ alpha + beta + gamma = pi $

$ x in RR, n in NN, z in CC $

$ partial / partial x integral_(-oo)^oo f(x) dif x $

$ A and B or not C $
