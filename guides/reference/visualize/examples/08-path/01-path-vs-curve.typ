// Note: `path` is deprecated. This example is here for reference only.
// Compiling will emit a deprecation warning; that is expected.
#set page(width: 14cm, height: auto, margin: 8pt)

== Equivalent shape drawn two ways

#stack(
  dir: ltr, spacing: 12pt,

  // Old: path
  path(
    fill: blue.lighten(80%),
    stroke: blue,
    closed: true,
    (0pt, 50pt),
    (100pt, 50pt),
    ((50pt, 0pt), (40pt, 0pt)),
  ),

  // New: curve
  curve(
    fill: blue.lighten(80%),
    stroke: blue,
    curve.move((0pt, 50pt)),
    curve.line((100pt, 50pt)),
    curve.cubic(auto, (40pt, 0pt), (50pt, 0pt)),
    curve.close(),
  ),
)
