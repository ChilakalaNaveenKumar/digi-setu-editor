// Math STYLES (italic / upright / bold). These are math-mode equivalents
// of bold/italic; they switch between the OpenType variants stored in the
// math font.
//
//   upright(body)   non-italic letters
//   italic(body)    italic letters (default for roman + greek lowercase)
//   bold(body)      bold variant

= upright vs default italic

$ upright(A) != A $

= bold

$ bold(A) := B^+ $

= Side-by-side comparison

$ A B C quad upright(A B C) quad bold(A B C) quad bold(upright(A B C)) $

= Forcing italic on something Typst defaults to upright

$ italic("OpenType") $
// Quoted identifiers default to upright; italic() makes them italic.
