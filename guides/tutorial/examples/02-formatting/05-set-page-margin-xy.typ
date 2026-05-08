// Demonstrates: dictionary-typed argument 'margin' using axis shorthand.
// 'x' applies to both left and right; 'y' applies to both top and bottom.
// Dictionary literals use (key: value, key: value, ...) syntax.

#set page(
  paper: "a6",
  margin: (x: 1.8cm, y: 1.5cm),
)

= Symmetric Margins
Horizontal margins (x) and vertical margins (y) are
applied symmetrically.
