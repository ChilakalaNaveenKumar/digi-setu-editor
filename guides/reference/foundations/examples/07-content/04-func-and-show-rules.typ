// Every content value remembers WHICH element function created it.
// Access it with '.func()'. You can compare that to a global function
// to discriminate kinds in show rules.
//
// '.func()' is also exactly what 'set' and 'show' rules target:
//   set heading(numbering: "1.")
//   show heading: it => ...
//
// Inside a show rule, 'it' is the matched content. You can read its
// fields ('it.level', 'it.body', etc.) and emit replacement content.

#let h = heading("Intro")
h.func() == heading: #(h.func() == heading)
h.func() == text:    #(h.func() == text)

#show heading: it => [LEVEL #it.level | #it.body]

= Introduction
== Setup
=== Background
