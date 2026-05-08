// 'outline.entry' is one entry in the listing. Default show rule:
//
//   #show outline.entry: it => link(
//     it.element.location(),
//     it.indented(it.prefix(), it.inner()),
//   )
//
// Helper functions on the entry:
//   it.indented(prefix, inner)  laid-out indent + alignment
//   it.prefix()                 number + supplement
//   it.inner()                  body + fill + page number
//   it.body()                   just the title text
//   it.page()                   just the page number
//   it.fill                     fill content (default: dotted repeat)
//
// Common customizations:
//   - top-level entries get extra spacing
//   - drop the dotted leader and page number entirely

#set heading(numbering: "1.")

// Top-level entries get more space.
#show outline.entry.where(level: 1): it => {
  v(0.4em, weak: true)
  strong(it)
}

// Replace the dotted leader with a solid line.
#set outline.entry(fill: box(width: 1fr)[#line(length: 100%, stroke: 0.4pt)])

#outline()

= About ACME Corp.
== History
=== Origins
= Products
== ACME Tools

#pagebreak()

= No-page-number outline (titles only)

#show outline.entry: it => link(
  it.element.location(),
  it.indented(it.prefix(), it.body()),
)
#set outline.entry(fill: none)

#outline()
