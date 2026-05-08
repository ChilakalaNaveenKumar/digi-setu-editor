// 'relative' is a TYPE that combines a 'length' and a 'ratio'.
//   25%        is a relative (ratio only, length component is 0pt)
//   1cm        is a relative (length only, ratio component is 0%)
//   25% + 1cm  is a relative (both)
//
// Wherever a 'relative' is expected, you can pass a bare length OR a
// bare ratio. Mixing them is fine.

= Relative widths

#rect(width: 25%)             // 25% of container width
#rect(width: 25% + 1cm)        // 25% of container + 1cm
#rect(width: 100% - 2cm)       // full width minus 2cm

= Relative-to-page vs relative-to-container

The percentage is relative to whichever container the element sits in:

#rect(width: 50%)              // 50% of the PAGE inner width

#block(width: 100pt, fill: aqua)[
  #rect(width: 50%)            // 50% of the BLOCK width = 50pt
]

= Multiplication scales BOTH parts

#((100% + 4pt) * 2)            // -> 200% + 8pt
#((50% + 2pt) * 0.5)           // -> 25% + 1pt

= Inspect the parts

#((100% - 50pt).length)        // -> -50pt   (the length component)
#((100% - 50pt).ratio)         // -> 100%    (the ratio component)
