// 'measure(content, width: auto, height: auto)' returns the laid-out
// SIZE of content (a dictionary with 'width' and 'height' lengths).
//
// Requires 'context' since the result depends on font, page, etc.
//
// width: / height: bound the measurement region. 'auto' = unbounded.
//
// Pitfall: passing a sized 'block(content, width: ...)' returns the
// BLOCK'S dimensions, not the inner content's. To measure the inner
// content under a width constraint, pass the content + the 'width:' arg
// instead.

= Measure depends on text size

#let s = [Hello!]
#s
#set text(14pt)
#s

#let thing(body) = context {
  let size = measure(body)
  [Width of "#body" is #size.width]
}

#thing[Hey] \
#thing[Welcome] \
#thing[Welcome to the home page]

= Bound the layout width

#context measure(lorem(50)).height                       // unbounded -> very wide / shallow
#linebreak()
#context measure(lorem(50), width: 300pt).height          // 300pt-wide measurement

= Measuring vs measuring a sized block

#context measure(lorem(50), width: 200pt)                  // measures inner content under 200pt
#linebreak()
#context measure(block(lorem(50), width: 200pt))           // measures the block (200pt wide)
