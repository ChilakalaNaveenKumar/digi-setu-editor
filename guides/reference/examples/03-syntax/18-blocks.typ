// Demonstrates: code block { ... } vs content block [ ... ].
// Code blocks evaluate multiple expressions; their output values are JOINED
// (concatenated) into a single value. 'let' bindings yield 'none' which
// joins as no-op. Content blocks hold markup that can be stored or passed.

#{
  let prefix = "Build "
  let n = 1407
  prefix + str(n) + ": "
  [*green*]
}

#let header = [== Section header from a content block]
#header
