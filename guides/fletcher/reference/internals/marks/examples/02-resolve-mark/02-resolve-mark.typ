// Internals/marks 02 — resolve-mark output.

#import "@preview/fletcher:0.5.8" as fletcher
#set page(width: auto, height: auto, margin: 6pt)

#context fletcher.resolve-mark((
  a: 1,
  b: 2,
  c: mark => mark.a + mark.b,
))
