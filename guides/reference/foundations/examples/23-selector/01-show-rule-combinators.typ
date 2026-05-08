// A SELECTOR picks elements out of the document. Source forms:
//   element_function                    e.g. heading, figure, list, link
//   element_function.where(field: ...)  e.g. heading.where(level: 1)
//   <label>                             a bare label is itself a selector
//   "string" or regex("...")            matches text content
//   selector(any-of-the-above)          explicit constructor; lets you call
//                                       .or(), .and(), .before(), .after()
//
// Combinators on a selector value:
//   .or(s, ...)           union: match this OR any other
//   .and(s, ...)          intersection: match this AND all others
//                          (most useful when mixing kind constraint + label)
//   .before(end, inclusive: bool)
//   .after(start, inclusive: bool)
//
// Show rules accept any selector:

#show heading.where(level: 1): set text(fill: navy)
#show heading.where(level: 1).or(heading.where(level: 2)): set text(weight: "bold")
#show <hot>: it => box(
  fill: rgb("#ffeb3b"),
  inset: (x: 4pt, y: 1pt),
  it,
)

= Top heading

== Sub heading

=== Sub-sub heading (no rule fires)

Inline #text[hot phrase]<hot> in a paragraph.
