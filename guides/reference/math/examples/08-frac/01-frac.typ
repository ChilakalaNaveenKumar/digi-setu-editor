// 'frac(num, denom, style: "vertical")' renders a fraction.
//
// SHORTHAND syntax: a / b. Group with parens to combine multiple atoms.
//   1/2          -> 1 over 2
//   (x+1)/2      -> (x+1) over 2     (parens removed)
//   ((x+1))/2    -> nest to PRESERVE the parens
//
// 'style' values:
//   "vertical"    stacked with bar (default)
//   "skewed"      slanted bar a/b
//   "horizontal"  inline a/b (parentheses retained)

= Slash shorthand vs frac()

$ 1/2 < (x+1)/2 $
$ ((x+1)) / 2 = frac(a, b) $

= Style variants

$ frac(x, y, style: "vertical")  quad
  frac(x, y, style: "skewed")    quad
  frac(x, y, style: "horizontal") $

= Setting the default style globally

#set math.frac(style: "skewed")
$ a / b $
#set math.frac(style: "vertical")

= Inline fractions in horizontal style

#show math.equation.where(block: false): set math.frac(style: "horizontal")

This $(x - y)/z = 3$ is inline math using horizontal fractions, while the
block equation below stays vertical:

$ (x - y) / z = 3 $
