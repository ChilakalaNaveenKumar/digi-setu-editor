// Demonstrates: trailing content-block syntax sugar.
// '#fn(args)[content]' is equivalent to passing the bracketed markup
// as the LAST positional argument to fn(...). Common with text(), align(),
// box(), figure(), etc.

#text(font: "Libertinus Serif", size: 12pt)[
  = Quarterly Report
  Cold-start latency improved by 18% after the
  scheduler rewrite landed.
]
