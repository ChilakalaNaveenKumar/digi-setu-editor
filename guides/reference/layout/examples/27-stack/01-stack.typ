// 'stack(dir: ttb, spacing: none, ..children)' arranges children along
// an axis with optional spacing.
//
// dir       ttb (default), btt, ltr, rtl
// spacing   none | length | fraction
//   - omitted: no extra spacing between children
//   - explicit length: that gap between adjacent children
//
// You can ALSO inline an explicit spacing value AS one of the children:
//   stack(rect(...), 1cm, rect(...), 1fr, rect(...))

= Vertical stack (default ttb)

#stack(
  spacing: 4pt,
  rect(width: 40pt, height: 20pt, fill: aqua),
  rect(width: 80pt, height: 20pt, fill: orange),
  rect(width: 60pt, height: 20pt, fill: green.lighten(50%)),
)

= Horizontal stack (ltr)

#stack(
  dir: ltr,
  spacing: 4pt,
  rect(width: 30pt, height: 30pt, fill: aqua),
  rect(width: 30pt, height: 30pt, fill: orange),
  rect(width: 30pt, height: 30pt, fill: green.lighten(50%)),
)

= rtl reverses the apparent order

#stack(
  dir: rtl,
  spacing: 4pt,
  rect(width: 30pt, height: 30pt, fill: aqua)[A],
  rect(width: 30pt, height: 30pt, fill: orange)[B],
  rect(width: 30pt, height: 30pt, fill: green.lighten(50%))[C],
)

= Mixing fixed and fractional spacing as inline children

#set page(width: 250pt, height: auto)

#stack(
  dir: ltr,
  rect(width: 30pt, height: 20pt, fill: aqua),
  1fr,
  rect(width: 30pt, height: 20pt, fill: orange),
  20pt,
  rect(width: 30pt, height: 20pt, fill: green.lighten(50%)),
)
