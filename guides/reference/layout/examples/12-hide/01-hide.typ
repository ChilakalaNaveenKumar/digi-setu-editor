// 'hide(body)' makes content invisible while still occupying its layout space.
// AT (screen readers) ALSO won't see it.
//
// Use cases:
//   - reserve space exactly the size of some content
//   - quick visual redaction (NOT secure! see warning below)

= Reserve space the size of "Hello"

Hello Jane \
#hide[Hello] Joe
// Both lines have the same indent because 'hide[Hello]' takes the same
// width as the visible 'Hello' on the previous line.

= Aligning a column of values

#table(
  columns: 2,
  inset: 4pt,
  [Apples],   [3],
  [Pears],    [#hide[12]4],   // alignment-only padding before "4"
  [Cherries], [12],
)

= NOT for sensitive data

// 'hide()' visually removes content but the layout's metadata may
// still leak shape/length. Some PDF outlines, bookmarks, or selectable
// text might still preserve traces. Don't use 'hide' for true redaction.
This document discusses the salary of #hide[Bob the engineer who was paid 90k].
