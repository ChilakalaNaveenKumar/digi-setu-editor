// 'op(text, limits: false)' renders a TEXT operator (upright) inside math.
// Use it for operators that should be set in roman type, like 'sin', 'log',
// or your own custom one.
//
// Predefined operators (no need to call op() yourself):
//   arccos arcsin arctan arg cos cosh cot coth csc csch ctg deg det dim
//   exp gcd lcm hom id im inf ker lg lim liminf limsup ln log max min mod
//   Pr sec sech sin sinc sinh sup tan tanh tg tr
//
// 'limits: true' makes attachments behave as LIMITS (above/below) in
// block mode. Default is false (scripts beside).

= Predefined operators

$ tan x = (sin x) / (cos x) $
$ log_2 x = (ln x) / (ln 2) $
$ lim_(x -> 0) (sin x) / x = 1 $

= Custom operator with limits in block mode

$ op("custom", limits: #true)_(n -> oo) n $

= Custom operator without limits (default)

$ op("rank")(A) <= min(m, n) $

= Multi-letter identifier-as-operator pattern

#let argmin = math.op("argmin", limits: true)
$ argmin_(x in RR) f(x) $
