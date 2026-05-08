// 'par' configures paragraph behaviour. Most settings are tuned via
// 'set par(...)' rather than calling 'par(body)' directly. The most-used
// fields:
//
//   leading           length    line-to-line spacing inside a paragraph
//   spacing           length    paragraph-to-paragraph spacing
//   justify           bool      justify lines (with hyphenation if text.lang allows)
//   linebreaks        auto|"simple"|"optimized"
//   first-line-indent length | dictionary  first-line indent
//                          length form: only between consecutive paragraphs
//                          dict form: ('amount': len, 'all': bool) -- 'all: true'
//                                     applies to every paragraph
//   hanging-indent    length    indent for non-first lines

#set par(
  leading: 0.7em,
  spacing: 0.7em,
  justify: true,
  first-line-indent: 1.5em,
  hanging-indent: 0pt,
)

We proceed by contradiction. Suppose that there exists a set of positive
integers $a$, $b$, and $c$ that satisfies the equation $a^n + b^n = c^n$ for
some integer value of $n > 2$.

Without loss of generality, let $a$ be the smallest of the three integers.
Then we observe that ... and so the proof concludes.

Notice that the FIRST paragraph above is NOT indented (default behaviour:
only second-and-later consecutive paragraphs are). Switch to the dictionary
form to indent every paragraph.

#set par(first-line-indent: (amount: 1.5em, all: true))

#lorem(30)

#lorem(20)
