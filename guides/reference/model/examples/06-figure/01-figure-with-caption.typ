// 'figure(body, caption: ?, kind: ?, supplement: ?, numbering: "1", alt: ?,
//         placement: ?, scope: "column", gap: 0.65em, outlined: true)'
// wraps content with optional caption and ties it to a counter.
//
// Auto-detected kind:
//   image content -> kind: image    counter: figure.where(kind: image)
//   table content -> kind: table    counter: figure.where(kind: table)
//   raw content   -> kind: raw      counter: figure.where(kind: raw)
//   anything else -> default to 'image' kind
//
// Reference syntax: '@label' fetches the figure's number with localized
// supplement ("Figure 1", "Table 2", etc.).

#set heading(numbering: "1.")

= Image figure

@glacier shows the glacier image. Glaciers are complex systems.

#figure(
  image("_assets/sample.png", width: 60%),
  caption: [A curious image figure.],
) <glacier>

= Table figure (counter resets per kind)

#figure(
  table(
    columns: 4,
    table.header([t], [1], [2], [3]),
    [y], [0.3s], [0.4s], [0.8s],
  ),
  caption: [Timing results.],
) <timing>

= Custom kind

#figure(
  rect(width: 60pt, height: 40pt, fill: gray.lighten(60%))[Atom],
  caption: [A curious atom.],
  kind: "atom",
  supplement: [Atom],
) <atom>

References:
- @glacier  -> Figure 1 (image kind)
- @timing   -> Table 1  (table kind, separate counter)
- @atom     -> Atom 1   (custom kind, custom supplement)
