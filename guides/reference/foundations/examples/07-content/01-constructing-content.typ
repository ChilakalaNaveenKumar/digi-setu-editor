// 'content' is the type of every piece of document material. You produce it
// by writing markup, by calling element functions, or by enclosing markup in
// '[...]' brackets to capture it as a value.
//
// Content supports:
//   c1 + c2     -> sequence (concatenation)
//   c * n       -> repeat content n times (n is int)
//   The + operator joins content; in markup mode adjacent content is also
//   joined automatically.

Type of [*Hello!*] is #type([*Hello!*])

#let intro = [Welcome] + [, ] + [reader.]
Joined: #intro

#let dots = [. ] * 5
Repeated: #dots

#let block-of-paragraphs = [Para 1.] + parbreak() + [Para 2.]
#block-of-paragraphs
