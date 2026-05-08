// Internals/edge 01 — a "mark cheatsheet": every common shorthand
// the parser accepts, presented as a real comparison table.

#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge
#set page(width: auto, height: auto, margin: 6pt)

#let cheatsheet = (
  "->", "<-", "<->",
  "=>", ">->", "->>",
  "hook->", "hook'->", "|->",
  ">>--<<", "..>", "==>",
)

#let row(y, marks) = (
  fletcher.node((0, y), text(7pt, raw(marks))),
  fletcher.edge((1, y), (2.6, y), marks),
)

#let entries = cheatsheet.enumerate().map(((y, m)) => row(y, m)).flatten()

#diagram(
  spacing: (8mm, 6mm),
  ..entries,
)
