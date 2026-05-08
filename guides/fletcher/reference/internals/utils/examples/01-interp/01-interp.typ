// Internals/utils 01 — `interp` produces in-array and out-of-array
// values. Compare against a small "ruler" diagram.

#import "@preview/fletcher:0.5.8" as fletcher: diagram, node

#set page(width: auto, height: auto, margin: 6pt)

#let centers = (0pt, 1cm, 3cm)

#table(
  columns: 2,
  align: (left, right),
  [`interp(centers, 0)`],   [#fletcher.interp(centers, 0)],
  [`interp(centers, 0.5)`], [#fletcher.interp(centers, 0.5)],
  [`interp(centers, 1)`],   [#fletcher.interp(centers, 1)],
  [`interp(centers, 1.5)`], [#fletcher.interp(centers, 1.5)],
  [`interp(centers, 2)`],   [#fletcher.interp(centers, 2)],
  [`interp(centers, 3, spacing: 1cm)`], [#fletcher.interp(centers, 3, spacing: 1cm)],
  [`interp(centers, -1, spacing: 1cm)`], [#fletcher.interp(centers, -1, spacing: 1cm)],
)
