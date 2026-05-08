// Two more knobs:
//
// 1) Allow long block equations to break across pages (default: NO).
//    #show math.equation: set block(breakable: true)
//
// 2) 'alt:' on math.equation provides natural-language description for
//    Assistive Technology when exporting to PDF/HTML.

#show math.equation: set block(breakable: true)

= Long derivation that may break across pages

$ sum_(k=0)^n k
    &= 1 + 2 + 3 + dots + n \
    &= (n(n + 1)) / 2 \
    \
  product_(k=1)^n k
    &= 1 dot 2 dot 3 dot dots dot n \
    &= n! \
    \
  integral_0^1 x^2 dif x
    &= [x^3 / 3]_0^1 \
    &= 1/3 $

= Equation with alt text

#math.equation(
  alt: "integral from 1 to infinity of a x squared plus b with respect to x",
  block: true,
  $ integral_1^oo a x^2 + b dif x $,
)
