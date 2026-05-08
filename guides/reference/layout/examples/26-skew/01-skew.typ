// 'skew(ax: 0deg, ay: 0deg, origin: center + horizon, reflow: false, body)'
// applies horizontal/vertical skewing.
//
// Like 'rotate' / 'scale': layout is unaffected unless 'reflow: true'.

= Fake italic

#skew(ax: -12deg)[
  This is some fake-italic text.
]

= Horizontal vs vertical skew

A #skew(ax: 30deg)[H-skewed] B \
A #skew(ay: 30deg)[V-skewed] B \
A #skew(ax: 15deg, ay: -10deg)[both] B

= Origin alignment

X #box(skew(ax: -30deg, origin: center + horizon)[X]) X \
X #box(skew(ax: -30deg, origin: bottom + left)[X]) X \
X #box(skew(ax: -30deg, origin: top + right)[X]) X

= reflow: true makes the box accommodate the skew

Hello #skew(ay: 30deg, reflow: true, "World")!
