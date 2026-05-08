// 'heading(body, level: auto, depth: 1, offset: 0, numbering: none, ...)'
// creates a section heading.
//
// MARKUP SHORTHAND: lines starting with one or more '=' followed by a SPACE.
//   = Foo      -> depth 1
//   == Foo     -> depth 2
//   === Foo    -> depth 3
//
// Levels are computed as: level = offset + depth (unless 'level' is set
// explicitly). 'depth' is the relative nesting (set by the syntax); 'offset'
// shifts the whole subtree.
//
// Numbering: 'numbering:' accepts a numbering pattern string OR a function.
// Same shape as the 'numbering()' function.

#set heading(numbering: "1.a)")

= Introduction

In recent years, ...

== Preliminaries

To start, ...

= Method

Detailed description.

== Setup
=== Hardware
=== Software

== Procedure

== Results

= Conclusion
