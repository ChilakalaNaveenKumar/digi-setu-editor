// 'layout(fn)' gives you the OUTER container's dimensions.
//   fn receives a dictionary { width: <length>, height: <length> }
//   and is implicitly run with 'context'.
//
// Inside a normal page, 'size' is the page area minus margins.
// Inside a 'box(width: W, height: H)', 'size' is (W, H).
// To get the REMAINING height of the page, wrap in 'block(height: 1fr)'.

= Measure content using the current width

#let text = lorem(30)
#layout(size => [
  #let (height,) = measure(width: size.width, text)
  This text is #height high at the current page width: \
  #text
])

#pagebreak()

= Get the remaining page height

#set page(height: 200pt)
#lorem(20)

#block(height: 1fr, layout(size => [
  Remaining height: #size.height
]))

#pagebreak()

= Resolve a ratio to a fixed length

#layout(size => {
  let half = 50% * size.width
  [Half the page is #half wide.]
})
