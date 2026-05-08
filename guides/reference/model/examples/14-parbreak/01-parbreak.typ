// 'parbreak()' starts a new paragraph. In MARKUP, a blank line is the
// idiomatic way; you only call parbreak() explicitly inside CODE blocks
// (loops, helper functions) where blank lines aren't available.
//
// Multiple consecutive parbreaks COLLAPSE into one. Don't try to "add space"
// by calling parbreak() repeatedly -- use #v(amount) for vertical spacing.

Markup form (blank line):

First paragraph.

Second paragraph.

Code form (parbreak() inside a for loop):

#for i in range(3) {
  [Item #i: ]
  lorem(8)
  parbreak()
}

Multiple parbreaks collapse:

#parbreak()
#parbreak()
#parbreak()

Only ONE break above. To force more space, use:

#v(2em)

After 2em vertical space.
