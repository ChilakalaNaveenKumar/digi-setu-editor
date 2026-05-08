// Tutorial 08 — Touying static stand-in.
// Renders the final state of the slide so the file compiles without
// pulling in Touying. See the .md page for the actual slide recipe.

#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
#set page(width: auto, height: auto, margin: 6pt)

#diagram(
  node((0, 0), name: <A>)[$A$],
  edge("->"),
  node((1, 0), name: <B>)[$B$],
  edge("->"),
  node((2, 0), name: <C>)[$C$],
  edge(<A>, "~", <B>, bend: 40deg, stroke: red),
  edge(<B>, "~", <C>, bend: 40deg, stroke: green),
  edge(<C>, "~", <A>, bend: 40deg, stroke: blue),
)
