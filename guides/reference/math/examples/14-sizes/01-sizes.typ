// FORCED size styles for sub-expressions in math:
//   display(body, cramped: false)    -> normal block-equation size
//   inline(body,  cramped: false)    -> normal inline-equation size
//   script(body,  cramped: true)     -> sub/superscript size
//   sscript(body, cramped: true)     -> second-level script size
//
// 'cramped: true' constrains exponent height (mirrors how real
// scripts/sscripts are typeset).

= display() makes inline content render block-sized

$ sum_i x_i / 2 = display(sum_i x_i / 2) $
// LHS uses inline sizing inside an inline equation.
// RHS forces display sizing -- the limits go above/below.

= inline() makes block content render inline-sized

$ sum_i x_i / 2
    = inline(sum_i x_i / 2) $

= script() and sscript() shrink content

$ sum_i x_i / 2 = script(sum_i x_i / 2) $
$ sum_i x_i / 2 = sscript(sum_i x_i / 2) $
