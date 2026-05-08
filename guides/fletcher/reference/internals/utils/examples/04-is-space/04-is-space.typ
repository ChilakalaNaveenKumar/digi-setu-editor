// Internals/utils 04 — quick truth-table for is-space.

#import "@preview/fletcher:0.5.8" as fletcher
#set page(width: auto, height: auto, margin: 6pt)

#table(
  columns: 2,
  align: (left, right),
  [Input], [is-space?],
  [`[ ]`],         [#fletcher.is-space([ ])],
  [`[\ ]` (linebreak)], [#fletcher.is-space([ \ ])],
  [`[ A ]` (text)],     [#fletcher.is-space([ A ])],
  [`[hello]`],     [#fletcher.is-space([hello])],
  [`[]` (empty)],  [#fletcher.is-space([])],
)
