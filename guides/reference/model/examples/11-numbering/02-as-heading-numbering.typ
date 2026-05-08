// Pattern strings AND functions are interchangeable wherever Typst takes a
// "numbering" parameter: heading.numbering, figure.numbering, enum.numbering,
// math.equation.numbering, page.numbering, par.line.numbering, etc.
//
// This example puts both forms through the heading parameter.

= 1. String pattern

#set heading(numbering: "1.a)")

= First section
== Sub one
== Sub two
= Second section
== Sub three

= 2. Function pattern (unary tally marks)

#let unary(..nums) = "|" * nums.pos().last()
#set heading(numbering: unary)

= First   // |
= Second  // ||
= Third   // |||
