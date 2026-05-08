// 'std' is the built-in module that contains EVERY globally accessible item
// (every element function, every value like 'auto'/'none', etc.).
//
// You reach for it whenever a local name SHADOWS a built-in one. The classic
// case: a function parameter named 'text' would clobber the 'text' element
// inside its body. 'std.text' bypasses the shadow and gets you the original.

#let special(text) = {
  set std.text(style: "italic", fill: blue)
  set std.par.line(numbering: "1")
  text
}

#special[
  This paragraph is rendered with 'std.text' settings even though 'text'
  is locally rebound to the parameter content.

  A second wrapped line proves the per-line numbering set rule applied.
]

After: #lorem(8)
