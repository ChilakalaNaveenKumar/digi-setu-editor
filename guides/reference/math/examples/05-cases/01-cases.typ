// 'cases(..children, delim: ("{", "}"), reverse: false, gap: 0.2em)'
// renders a piecewise / case-distinction expression.
//
// Each comma-separated argument is a branch. Use '&' inside a branch
// to create alignment columns shared across branches.

= Standard cases

$ f(x, y) := cases(
  1 "if" (x dot y) / 2 <= 0,
  2 "if" x "is even",
  3 "if" x in NN,
  4 "else",
) $

= Aligned columns inside cases

$ abs(x) := cases(
  x   & "if" x >= 0,
  -x  & "if" x < 0,
) $

= Custom delimiter

#set math.cases(delim: "[")
$ x = cases(1, 2) $
#set math.cases(delim: ("{", "}"))

= Reversed (delimiter on the right)

#set math.cases(reverse: true)
$ cases(1, 2) = x $
#set math.cases(reverse: false)

= Wider gap between branches

#set math.cases(gap: 1em)
$ x = cases(1, 2, 3) $
