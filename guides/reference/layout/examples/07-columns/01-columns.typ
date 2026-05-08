// 'columns(count, gutter: 4%, body)' splits a CONTAINER into equally
// sized columns. Use 'colbreak()' to explicitly continue in the next column.
//
// For DOCUMENT-WIDE columns, prefer 'page(columns: N)' so pagebreaks,
// footnotes, and line numbering keep working.
//
// To "break out" to a single span across all columns (e.g. paper title),
// use 'place(scope: "parent", float: true, ...)'.

#set page(height: 200pt)

= Local 2-column block

#columns(2, gutter: 8pt)[
  This text is in the first column.

  #colbreak()

  This text is in the second column.
]

#pagebreak()

= Page-level columns + parent-scoped title

#set page(columns: 2)

#place(
  top + center,
  scope: "parent",
  float: true,
  text(1.4em, weight: "bold")[My document title spans both columns],
)

#lorem(40)
