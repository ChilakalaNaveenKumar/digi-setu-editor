// 'cancel(body, length: 100% + 3pt, inverted: false, cross: false,
//         angle: auto, stroke: 0.5pt)'
// draws a diagonal line over content -- typically to show elimination.
//
// length    relative   line length, relative to the diagonal of the box
// inverted  bool       flip along Y axis (top-left direction)
// cross     bool       draw two lines forming an X (overrides 'inverted')
// angle     auto|angle|fn   rotation w.r.t. y-axis. fn(default_angle) -> angle
// stroke    stroke     standard stroke spec

= Eliminating a common factor

Here, we can simplify:
$ (a dot b dot cancel(x)) / cancel(x) $

= Length, inverted, cross

$ a + cancel(x, length: #200%) - cancel(x, length: #200%) $

$ (a cancel((b + c), inverted: #true)) / cancel(b + c, inverted: #true) $

$ cancel(Pi, cross: #true) $

= Custom angles

$ cancel(Pi, angle: #0deg) quad
  cancel(Pi, angle: #45deg) quad
  cancel(Pi, angle: #90deg) $

$ cancel(1/(1+x), angle: #(a => a + 45deg)) $

= Custom stroke (color, thickness, dash)

$ cancel(
  sum x,
  stroke: #(paint: red, thickness: 1.5pt, dash: "dashed"),
) $
