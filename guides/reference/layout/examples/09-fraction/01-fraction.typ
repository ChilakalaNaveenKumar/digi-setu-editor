// 'fraction' is a TYPE for the 'fr' unit -- distributes REMAINING space
// among fractionally sized siblings according to their relative weights.
//
// Common locations:
//   h(1fr)        flexible horizontal spacing in a paragraph
//   v(1fr)        flexible vertical spacing in a flow
//   block(height: 1fr)              fill remaining vertical space
//   columns: (1fr, 2fr, auto)       grid columns with weighted widths
//   box(width: 1fr)                  flexible box width inside a paragraph

= h(1fr) inside a paragraph

Left #h(1fr) Middle #h(1fr) Right \
A #h(1fr) B #h(1fr) C #h(1fr) D \
A #h(2fr) B #h(1fr) C        // B aligns 1/3 from the right edge

= grid columns with mixed sizing

#grid(
  columns: (auto, 1fr, 2fr),
  fill: (x, _) => if calc.even(x) { luma(240) } else { white },
  inset: 4pt,
  [auto], [1fr], [2fr],
  [Tag], [middle column], [twice as wide as the middle one],
)

= block(height: 1fr) fills remaining page height

#set page(height: 200pt)
#lorem(20)
#block(height: 1fr, fill: aqua, [I fill the remaining vertical space.])
