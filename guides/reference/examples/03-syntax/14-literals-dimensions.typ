// Demonstrates: dimension and ratio literals.
//   length:   pt, mm, cm, in, em (font-relative)
//   angle:    deg, rad
//   fraction: <n>fr  (used by grid columns, etc.)
//   ratio:    <n>%   (relative to surrounding context)

#let absolute-len = 12pt
#let metric-len = 1.5cm
#let imperial-len = 0.5in
#let font-len = 1.2em
#let right-angle = 90deg
#let one-rad = 1rad
#let two-fr = 2fr
#let three-quarters = 75%

Sample lengths: #absolute-len, #metric-len, #imperial-len, #font-len.
Angles: #right-angle, #one-rad. Fraction: #two-fr. Ratio: #three-quarters.
