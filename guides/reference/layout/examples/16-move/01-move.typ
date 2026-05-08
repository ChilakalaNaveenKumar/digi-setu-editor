// 'move(dx: 0pt, dy: 0pt, body)' shifts content visually without
// affecting layout. Surrounding elements are sized AS IF the content
// stayed at its original position.
//
// Positive dx -> right, positive dy -> down.
//
// AT (screen readers) read content in source order, ignoring any
// movement.

= Drop-shadow effect

#rect(inset: 0pt, fill: gray, move(
  dx: 4pt, dy: 6pt,
  rect(
    inset: 8pt,
    fill: white,
    stroke: black,
    [Abra cadabra],
  ),
))

= Move doesn't change line height

Hello #move(dy: -3pt)[up] world! \
Hello #move(dy: 3pt)[down] world!

= Negative offsets

#rect(width: 60pt, height: 30pt, fill: aqua, move(
  dx: -5pt, dy: -5pt,
  rect(width: 60pt, height: 30pt, fill: orange, [shifted]),
))
