// 'h(amount, weak: false)' inserts horizontal spacing into a paragraph.
// 'amount' can be:
//   - absolute length    (1cm, 12pt)
//   - relative           (30%)
//   - fraction (fr)      flexible space; distributes leftover horizontal space

= Absolute and relative

First #h(1cm) Second \
First #h(30%) Second

= Fractional spacing (alignment without a paragraph break)

First #h(1fr) Second \
First #h(1fr) Second #h(1fr) Third \
First #h(2fr) Second #h(1fr) Third       // Second is 2/3 across

= Math constants (only inside math mode)

$ a thin b quad a med b quad a thick b quad a quad b quad a wide b $
//   thin = 1/6em, med = 2/9em, thick = 5/18em, quad = 1em, wide = 2em

= Weak spacing (collapses at edges and against other weak spaces)

#h(1cm, weak: true)
We identified a group of _weak_ specimens that fail to manifest in most
cases. However, when#h(8pt, weak: true) supported#h(8pt, weak: true) on
both sides, they do show up.

Further#h(0pt, weak: true) more, even the smallest of them swallow
adjacent markup spaces.
