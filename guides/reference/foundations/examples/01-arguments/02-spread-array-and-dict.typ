// Demonstrates: the spread operator '..' at a CALL SITE expands an array,
// dictionary, or arguments value into individual arguments.
//   ..array  -> positional arguments
//   ..dict   -> named arguments
//   ..args   -> both, preserving positional and named

#let nums = (12, 4, 7, 19)
Min of #nums is #calc.min(..nums).

#let text-style = (fill: blue, weight: "bold")
#text(..text-style)[Highlighted body text]
