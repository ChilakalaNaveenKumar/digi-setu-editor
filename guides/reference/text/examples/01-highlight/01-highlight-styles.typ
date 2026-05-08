// 'highlight(body, fill: ?, stroke: (:), top-edge: "ascender",
//            bottom-edge: "descender", extent: 0pt, radius: (:))'
// draws a colored background behind text.
//
// Most-used fields:
//   fill         color | gradient | tiling | none    background paint (default semi-transparent yellow)
//   stroke       border around the highlight (rect-style stroke value)
//   top-edge     "ascender" | "cap-height" | "x-height" | "baseline" | "bounds"
//   bottom-edge  "descender" | "baseline" | "bounds"
//   extent       length    extra width on each side (negative = trim inward)
//   radius       relative | dictionary    rounded corners

This is #highlight[important].

Custom color: This is #highlight(fill: rgb("#aef"))[blue-tinted].

Stroked: a #highlight(stroke: 0.5pt + fuchsia)[stroked highlight].

Padded + rounded:
listen #highlight(radius: 5pt, extent: 2pt)[carefully], it will be on the test.

Edge tuning (x-height to baseline -- tighter band hugging lowercase letters):

#set highlight(top-edge: "x-height", bottom-edge: "baseline")
#highlight[a] #highlight[aib] #highlight[ap]
