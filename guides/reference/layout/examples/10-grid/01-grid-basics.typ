// 'grid' arranges content in a 2-D track grid (cells filled row-major).
// It shares its core API with 'table' but is intended for LAYOUT, not
// data presentation -- grids carry no semantic meaning to AT.
//
// Track sizing values:
//   auto                    fit content (will share leftover space if multiple)
//   length / relative       fixed
//   fr (fraction)           share remaining space proportionally
//
// Shorthands:
//   columns: 3              -> (auto, auto, auto)
//   rows: ()                -> auto for any extra cells
//
// Most-used fields:
//   columns / rows / gutter / column-gutter / row-gutter
//   inset / align / fill / stroke
// All "per-cell" fields (inset, align, fill, stroke) accept
//   - a single value, or
//   - an array (cycled across columns), or
//   - a function (x, y) => value.

#set page(width: 320pt, height: auto)

= Mixed track sizing

#grid(
  columns: (60pt, 1fr, 2fr),
  rows: (auto, 60pt),
  gutter: 3pt,
  rect(inset: 8pt, fill: luma(220), width: 100%)[Fixed width],
  rect(inset: 8pt, fill: luma(220), width: 100%)[1/3 of remains],
  rect(inset: 8pt, fill: luma(220), width: 100%)[2/3 of remains],
  rect(inset: 8pt, fill: luma(220), width: 100%, height: 100%)[Fixed height],
  grid.cell(
    colspan: 2,
    rect(inset: 8pt, fill: aqua, width: 100%, height: 100%)[colspan: 2],
  ),
)

= Spread an array into a grid

#grid(
  columns: 5,
  gutter: 5pt,
  inset: 4pt,
  fill: luma(245),
  ..range(15).map(str),
)
