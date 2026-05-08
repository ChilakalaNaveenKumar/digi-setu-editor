// 'accent(base, accent, size: 100% + 0pt, dotless: true)' attaches an
// accent (hat, tilde, arrow, dot, ...) to a base.
//
// Common shortcuts (each is a function that calls 'accent' under the hood):
//   grave(x)   acute(x)   hat(x)    tilde(x)
//   macron(x)  dash(x)    breve(x)  dot(x)
//   dot.double(x) | diaer(x)
//   acute.double(x)        caron(x)
//   arrow(x)   arrow.l(x)  arrow.l.r(x)
//   harpoon(x) harpoon.lt(x)
//
// The 'accent' parameter accepts a SYMBOL (e.g. 'arrow') or a literal char
// in backticks (e.g. ``  ``) or a Unicode escape (e.g. "\u{0303}" for tilde).

= Built-in shortcuts

$ grave(a) = accent(a, `) $
$ arrow(a) = accent(a, arrow) $
$ tilde(a) = accent(a, \u{0303}) $

= Multi-letter base (size: 100% by default)

$ arrow(A B C) $

= Tuning size

$ dash(A) quad dash(A, size: #150%) $

= Dotless lowercase under top accent (default ON)

$ hat(i) quad hat(j) quad hat(dotless: #false, i) $

= Bag of common accents

$ hat(x) quad tilde(x) quad bar(x) quad
  dot(x) quad dot.double(x) quad
  arrow(x) quad arrow.l(x) quad arrow.l.r(x) $
