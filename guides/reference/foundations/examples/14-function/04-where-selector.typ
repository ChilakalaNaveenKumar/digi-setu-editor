// element_function.where(field: value, ...) -> selector that matches
// elements of that function whose explicitly-set fields equal the values.
//
// The result is a SELECTOR, not a function. It plugs into:
//   show <selector>: ...        (show rules)
//   query(<selector>)           (introspection queries)

#show heading.where(level: 2): set text(blue)
#show heading.where(level: 3): set text(gray)

= Section title (level 1, default color)
== Subsection (matched: blue)
=== Sub-subsection (matched: gray)
==== Even deeper (level 4, default color)
