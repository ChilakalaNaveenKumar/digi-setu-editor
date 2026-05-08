// Show rules can target headings by element function or by '.where()' on the
// 'level' field. Inside the show handler, you typically WRAP the body in a
// 'block' so headings stay non-orphan (they get an implicit show-set rule
// that makes their wrapping block 'sticky', preventing page-end orphans).

#set heading(numbering: "1.a")

#show heading.where(level: 1): it => {
  set text(fill: navy, size: 1.4em, weight: "bold")
  block(below: 0.6em, it)
}

#show heading.where(level: 2): set text(fill: maroon, style: "italic")

= Top section

== Subsection one
== Subsection two

= Another top section

== A subsection

=== Sub-sub (no rule fires; default style applies)
