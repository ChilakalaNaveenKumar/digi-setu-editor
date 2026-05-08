// 'repeat(body, gap: 0pt, justify: true)' fills the available space with
// repeated copies of 'body'. Useful for index leaders, dot-fills, and
// outline entries.
//
// Errors if the available space is unbounded (would create infinite content).
//
// AT marks repeated content as PDF artifact (hidden from screen readers).

= Dotted leader

Sign on the dotted line:
#box(width: 1fr, repeat[.])

#v(8pt, weak: true)
#align(right)[Berlin, the 22nd of December, 2026]

= With a custom gap

Item A #box(width: 1fr, repeat(gap: 4pt, "·")) page 1 \
Item B #box(width: 1fr, repeat(gap: 4pt, "·")) page 5 \
Item C #box(width: 1fr, repeat(gap: 4pt, "·")) page 11

= justify: false (no extra space inserted)

A #box(width: 1fr, repeat(justify: false)[--]) B
// With justify: false the body is stamped tightly until the space runs
// out; the rest of the slot is left blank.

= Custom outline-entry leader

#set heading(numbering: "1.")

#show outline.entry: it => link(
  it.element.location(),
  it.indented(
    it.prefix(),
    it.body() + box(width: 1fr, repeat(gap: 2pt)[·]) + it.page(),
  ),
)

#outline()

= Introduction
= Methods
= Results
