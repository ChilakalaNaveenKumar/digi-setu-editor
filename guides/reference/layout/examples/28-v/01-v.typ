// 'v(amount, weak: false)' inserts vertical spacing in a flow of blocks.
// 'amount' may be absolute (12pt), relative (40%), or fractional (1fr).
//
// 'weak: true' collapses at the top/bottom of a flow and against other
// weak spaces. Weak spaces also OVERRIDE adjacent paragraph spacing
// (no matter the size).

= Different spacing modes side-by-side

#grid(
  rows: 3cm,
  columns: 6,
  gutter: 1fr,
  [A #parbreak() B],
  [A #v(0pt) B],
  [A #v(10pt) B],
  [A #v(0pt, weak: true) B],
  [A #v(40%, weak: true) B],
  [A #v(1fr) B],
)

= Surrounding a math block with weak spaces

The following theorem is foundational to the field:
#v(4pt, weak: true)
$ x^2 + y^2 = r^2 $
#v(4pt, weak: true)
The proof is simple:

= Push content to the bottom of a page

#set page(height: 200pt)
Header text.
#v(1fr)
Bottom text.
