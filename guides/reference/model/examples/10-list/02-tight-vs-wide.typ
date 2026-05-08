// TIGHTNESS:
//   - In MARKUP, tightness is determined by whether items have BLANK LINES
//     between them.
//       items together  -> tight  (uses 'par.leading' for spacing)
//       blank line gap  -> wide   (uses 'par.spacing' for spacing)
//   - You CANNOT override the markup-driven tightness via 'set list(tight: ...)'.
//   - Tightness only affects the default 'spacing' resolution.
//
// To force wide spacing on a programmatically-built list, use 'list.item'
// with explicit 'spacing:' or assemble blocks yourself.

= Tight (no blank lines)

- short
- short
- short

= Wide (blank lines between items)

- a longer item with multiple words and ideas

- another wider item to demonstrate spacing

- one more

= Generated via for-loop (becomes a list)

#for letter in "ABC" [
  - Letter #letter
]

= Programmatic list with list.item

#list(
  list.item[Foundations],
  list.item[Data Loading],
  list.item[Layout],
)
