// 'box' is the INLINE-level container. Use it inside running text to:
//   - embed an image / svg / shape inline
//   - put a colored / bordered span around text
//   - reserve a fractional 'h(1fr)' width for a line/rule
//
// Most-used fields:
//   width    auto | relative | fraction         (only widths can be fractional!)
//   height   auto | relative
//   baseline relative                            shift content up/down
//   fill     none | color | gradient | tiling   background
//   stroke   stroke spec                         border
//   radius   length | dictionary                 corner rounding
//   inset    length | dictionary                 inner padding
//   outset   length | dictionary                 expand without affecting layout
//   clip     bool                                clip overflowing content

= Inline-only embeds

Refer to the docs #box(height: 9pt, fill: luma(240))[icon] for more
information.

= Inline-styled "rectangle" span

An inline #box(
  fill: luma(235),
  inset: (x: 3pt, y: 0pt),
  outset: (y: 3pt),
  radius: 2pt,
)[rectangle].

= Fractional width = horizontal rule that fills remaining space

Section heading #box(width: 1fr, line(length: 100%)) END

= Baseline shift

Image: #box(baseline: 40%, rect(width: 1cm, height: 1cm, fill: aqua)).

= Clip overflowing content

#box(
  width: 60pt, height: 30pt, clip: true,
  fill: luma(245),
)[A long line that overflows the small clipping box would normally spill out.]
