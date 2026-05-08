// Demonstrates: figure() takes a positional content arg + named caption.
// Inside an arg list we are in CODE mode: nested function calls drop the '#'.
// Markup as an argument is wrapped in [ ... ] -- a "content block".

#figure(
  image("_assets/sample.png", width: 50%),
  caption: [
    Sample placeholder asset used by the
    _writing-basics_ example suite.
  ],
)
