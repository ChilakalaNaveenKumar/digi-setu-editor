// 'length' is a TYPE for sizes & distances.
//
// Units:
//   pt   72pt = 1 inch
//   mm   millimeter
//   cm   centimeter
//   in   inch
//   em   relative to current font size (2em = 2 * font-size)
//
// Lengths can be ADDED / SUBTRACTED, and MULTIPLIED / DIVIDED by integers
// or floats. Mixing 'em' with absolute units is fine -- the result is
// stored as a sum.

= Literal lengths

#rect(width: 20pt, height: 12pt)
#rect(width: 2em, height: 1.5em)
#rect(width: 1in, height: 0.5in)

= Arithmetic and conversion

#(3em + 5pt).em                  // 3 (em-component as float)
#(20pt).em                        // 0
#(3em + 5pt).abs                  // 5pt (the absolute component)

= Convert pure absolute lengths

#(72pt).pt()      // -> 72.0
#(2.54cm).mm()    // -> 25.4
#(2.54cm).cm()    // -> 2.54
#(1in).inches()   // -> 1.0
// Calling .pt() / .mm() etc. on a length with non-zero 'em' fails;
// use .abs first:
#(3em + 5pt).abs.pt()    // -> 5.0

= Resolve em -> absolute via context

#set text(size: 12pt)
#context [
  #(6pt).to-absolute() \
  #(6pt + 10em).to-absolute() \
  #(10em).to-absolute()
]

#set text(size: 6pt)
#context [
  #(6pt).to-absolute() \
  #(6pt + 10em).to-absolute() \
  #(10em).to-absolute()
]
