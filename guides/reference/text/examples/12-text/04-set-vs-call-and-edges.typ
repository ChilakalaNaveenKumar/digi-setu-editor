// Two ways to use 'text':
//
//   #set text(...)              -- applies to all subsequent text in scope
//   #text(...)[body]            -- one-off scoped call (great for arguments)
//
// EDGE METRICS: 'top-edge' / 'bottom-edge' control the conceptual frame
// around text -- this affects how containers (rect, block, box) size around
// the text. Not visual height of glyphs themselves.
//
//   top-edge     "ascender" | "cap-height" | "x-height" | "baseline" | "bounds"
//                  default "cap-height" (so caps sit at the top of the box)
//   bottom-edge  "baseline" | "descender" | "bounds"
//                  default "baseline" (so descenders dangle below the box)
//
// 'baseline: length' shifts the entire text run up/down (positive = down).

= set vs call

#set text(weight: "bold")
This whole sentence is bold via set rule.

#text(weight: "regular")[but this part is back to regular] -- and back to bold.

#set text(weight: "regular")

= Edges control container sizing

#set rect(inset: 0pt)
#set text(size: 20pt)

top-edge "ascender" (taller box):
#text(top-edge: "ascender")[#rect(fill: aqua)[Typst]]

top-edge "cap-height" (default, snug to caps):
#text(top-edge: "cap-height")[#rect(fill: aqua)[Typst]]

bottom-edge "baseline" (default, descender drops out):
#text(bottom-edge: "baseline")[#rect(fill: aqua)[Typst]]

bottom-edge "descender" (full container):
#text(bottom-edge: "descender")[#rect(fill: aqua)[Typst]]

#set text(size: 11pt)

= Baseline shift

A #text(baseline: 3pt)[lowered] word inside the line.
A #text(baseline: -3pt)[raised] word inside the line.
