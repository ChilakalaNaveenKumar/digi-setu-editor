// Internals/utils 02 — round-trip interp ↔ interp-inv.

#import "@preview/fletcher:0.5.8" as fletcher

#set page(width: auto, height: auto, margin: 6pt)

#let centers = (0pt, 1cm, 3cm)

#table(
  columns: 3,
  align: (left, right, right),
  [Query], [interp-inv result], [round-trip via interp],
  [2cm],   [#fletcher.interp-inv(centers, 2cm)],
           [#fletcher.interp(centers, fletcher.interp-inv(centers, 2cm))],
  [0.5cm], [#fletcher.interp-inv(centers, 0.5cm)],
           [#fletcher.interp(centers, fletcher.interp-inv(centers, 0.5cm))],
  [3cm],   [#fletcher.interp-inv(centers, 3cm)],
           [#fletcher.interp(centers, fletcher.interp-inv(centers, 3cm))],
  [4cm with spacing: 1cm],
    [#fletcher.interp-inv(centers, 4cm, spacing: 1cm)],
    [#fletcher.interp(centers, fletcher.interp-inv(centers, 4cm, spacing: 1cm), spacing: 1cm)],
)
