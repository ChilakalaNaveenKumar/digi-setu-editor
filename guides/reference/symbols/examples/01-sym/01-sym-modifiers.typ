// 'sym' is a module of named symbols. In MARKUP, prefix with '#sym.':
//   #sym.arrow.r        -> →
// In MATH, drop the prefix:
//   $ arrow.r $          -> →
//
// MODIFIERS are accessed via dot notation. Most symbols have multiple
// variants reachable through chained modifiers:
//   arrow.r              ->
//   arrow.l              <-
//   arrow.l.r            <->
//   arrow.r.double       =>
//   arrow.r.long         long ->
//   arrow.r.squiggly     squiggly ->
//   arrow.r.tail         tailed ->
//   arrow.r.twohead      ->>
//
// Common modifier conventions seen across symbols:
//   .l / .r / .t / .b           direction
//   .double                     doubled glyph (=>, ⇒, ⟦)
//   .triple                     tripled
//   .long                       longer variant
//   .small                      smaller variant
//   .alt                        alternative form
//   .inv                        inverse / reversed
//   .filled / .stroked          filled vs outlined
//   .heavy / .bold              weight variants

= Common arrows

#sym.arrow.r quad #sym.arrow.l quad #sym.arrow.l.r quad
#sym.arrow.t quad #sym.arrow.b quad
#sym.arrow.r.double quad #sym.arrow.l.double quad
#sym.arrow.r.long quad #sym.arrow.r.tail quad #sym.arrow.r.twohead

= Number sets (blackboard bold)

#sym.NN quad #sym.ZZ quad #sym.QQ quad #sym.RR quad #sym.CC quad #sym.HH

= Greek letters (lowercase + uppercase)

#sym.alpha #sym.beta #sym.gamma #sym.delta #sym.epsilon ... #sym.omega

#sym.Alpha #sym.Beta #sym.Gamma #sym.Delta ... #sym.Omega

= Operators / relations

#sym.dot quad #sym.dot.c quad #sym.times quad #sym.div quad
#sym.plus.minus quad #sym.minus.plus quad #sym.eq.not quad
#sym.lt.eq quad #sym.gt.eq.not quad #sym.tilde.eq.not

= Brackets, fences, dots, ellipses

#sym.bracket.l #sym.bracket.r quad
#sym.bracket.l.double #sym.bracket.r.double quad
#sym.angle.l #sym.angle.r quad
#sym.dots.h quad #sym.dots.v quad #sym.dots.down quad #sym.dots.up

= Inside math (no #sym. prefix)

$ alpha + beta in NN quad x times y = z quad
  forall epsilon > 0 thin exists delta > 0 $

$ A subset.eq B quad C union D quad E sect F $

$ a arrow.l.r b quad p arrow.r.double q $
