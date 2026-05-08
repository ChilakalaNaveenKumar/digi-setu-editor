// 'table' arranges content in cells in row-major order. It shares its core
// mechanics with 'grid' but has cell-friendly defaults (visible stroke, 5pt
// inset).
//
// Most-used parameters:
//   columns       int | array<size>      column count or per-column sizes
//                                           (auto, length, ratio, fr fraction)
//   rows          int | array<size>      same for rows
//   gutter        size                   shorthand for column-gutter + row-gutter
//   inset         length | dict | array | function    cell padding
//   align         alignment | array | function        cell alignment
//   fill          color | array | function | none      cell background
//   stroke        stroke | array | function | none     cell borders
//
// Wrap with 'table.header(...)' (and optionally 'table.footer(...)') to mark
// header rows -- this is REQUIRED for accessibility and lets the header
// repeat across pages.

= Basic 4x4 table

#table(
  columns: 4,
  table.header(
    [], [*Q1*], [*Q2*], [*Q3*],
  ),
  [Revenue], [1000 €], [2000 €], [3000 €],
  [Expenses], [500 €], [1000 €], [1500 €],
  [Profit], [500 €], [1000 €], [1500 €],
)

= Mixed column sizes (1fr + auto + auto), inset, alignment

#table(
  columns: (1fr, auto, auto),
  inset: 10pt,
  align: horizon,
  table.header(
    [*Shape*], [*Volume*], [*Parameters*],
  ),
  [Cylinder],
  $ pi h (D^2 - d^2) / 4 $,
  [
    $h$: height \
    $D$: outer radius \
    $d$: inner radius
  ],
  [Tetrahedron],
  $ sqrt(2) / 12 a^3 $,
  [$a$: edge length],
)
