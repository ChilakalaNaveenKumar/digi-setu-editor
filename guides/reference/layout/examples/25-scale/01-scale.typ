// 'scale(factor: 100%, x: ?, y: ?, origin: center + horizon, reflow: false,
//        body)'
// scales content. Negative scale on an axis MIRRORS the content.
//
// Like 'rotate', the layout is unaffected unless reflow: true.
//
// 'factor' is a positional shorthand that sets x AND y to the same value.

= Mirroring with negative scale

#set align(center)
#scale(x: -100%)[This is mirrored.]
#scale(x: -100%, reflow: true)[This is mirrored, reflow: true.]

= Symmetric scale via positional 'factor'

A #scale(50%)[half] B \
A #scale(150%)[bigger] B \
A #scale(150%, reflow: true)[bigger reflow] B

= Per-axis scale

A #scale(x: 200%, y: 100%)[stretched] B \
A #scale(x: 100%, y: 200%)[tall] B

= Origin alignment

A#box(scale(75%)[A])A \
B#box(scale(75%, origin: bottom + left)[B])B
