// 'pad' adds spacing AROUND content. Distinct from 'block(inset: ...)':
// pad doesn't introduce a new visual container.
//
// Per-side: left, top, right, bottom
// Shorthands: x (= left+right), y (= top+bottom), rest (= all four)
//
// Precedence (when multiple are passed): per-side > x/y > rest

= Symmetric horizontal padding

#set align(center)

#pad(x: 16pt, rect(width: 60pt, height: 30pt, fill: aqua)[content])
_Padded with x: 16pt on each side._

= Per-side padding

#pad(
  left: 4pt, right: 16pt,
  top: 8pt, bottom: 24pt,
  rect(width: 60pt, height: 30pt, fill: orange),
)
_Different padding on each side._

= 'rest:' fills any side not specified

#pad(
  rest: 5pt,    // applies to all sides...
  top: 20pt,    // ...except 'top', which wins by precedence
  rect(width: 60pt, height: 30pt, fill: yellow),
)

= NEGATIVE padding (negative spacing)

#pad(x: -8pt, rect(width: 60pt, height: 30pt, fill: green.lighten(60%)))
// Negative pad pulls content OUT past its container's edge, useful for
// full-bleed images on otherwise-margined documents.
