// SHORTHAND attachment syntax (most common):
//   x_i      bottom (subscript)
//   x^2      top    (superscript)
//   x_i^2    both
//   x_(i+1)  group with parens
//
// SMART positioning: Typst decides whether to render top/bottom as scripts
// (sub/sup) or as LIMITS (above/below) based on the base.
//   - Large operators (sum, product, integral, lim) get LIMITS in BLOCK
//     equations, scripts in INLINE equations.
//   - Plain variables get SCRIPTS.
//
// Force the choice with 'limits()' / 'scripts()'.

= Inline behaviour (operators get scripts)

Inline: $sum_(i=0)^n a_i = 2^(1+i)$, also $product_(k=1)^N k = N!$.

= Block behaviour (operators get limits)

$ sum_(i=0)^n a_i = 2^(1+i) $
$ product_(k=1)^N k = N! $
$ lim_(x -> oo) 1/x = 0 $

= Forcing scripts in block mode

$ scripts(sum)_1^2 != sum_1^2 $

= Forcing limits in inline mode

Inline forced to limits: $limits(A)_1^2 != A_1^2$.

= Globally moving operator scripts to limits

#show math.equation.where(block: false): set math.op(limits: true)

Inline lim now uses limits: $lim_(x -> 0) f(x)$.
