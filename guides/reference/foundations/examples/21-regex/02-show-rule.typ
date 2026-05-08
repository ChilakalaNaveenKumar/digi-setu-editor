// A regex selector in a 'show' rule rewrites every text run that matches.
//
//   #show regex("..."): set text(...)              // restyle the match in place
//   #show regex("..."): match => [...transform...] // replace the match entirely
//
// The handler form receives the matched content (a 'text' element). Use it
// to wrap, replace, or annotate matches.

#show regex("\d+"): set text(fill: red, weight: "bold")
#show regex("\b(TODO|FIXME)\b"): m => box(
  fill: rgb("#ffeb3b"),
  inset: (x: 3pt, y: 0pt),
  text(weight: "bold")[#m],
)

The numbers 1, 42, and 1024 are highlighted in red.

TODO: write the section on grouping.
FIXME: clarify the escaping rules.
