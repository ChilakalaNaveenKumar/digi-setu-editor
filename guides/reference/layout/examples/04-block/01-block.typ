// 'block' is a BLOCK-level container. Use it to:
//   - put a background / border / radius around content
//   - size content explicitly
//   - control whether content can break across pages
//   - control vertical spacing around content (above / below)
//   - mark content as 'sticky' so it doesn't get orphaned
//
// Most-used fields:
//   width    auto | relative                     auto = take inner width
//   height   auto | relative | fraction          auto = fit content
//   fill     none | color | gradient | tiling    background
//   stroke   stroke spec                         border
//   radius   length | dictionary                 corner rounding
//   inset    length | dictionary                 inner padding
//   outset   length | dictionary                 expand without affecting layout
//   breakable bool                                break across pages (default: true)
//   sticky    bool                                stick to next block (default: false)
//   above / below   length | fraction            spacing around the block

= Background, padding, rounded corners

#set page(height: 200pt)
#block(
  fill: luma(230),
  inset: 8pt,
  radius: 4pt,
  width: 100%,
  lorem(15),
)

#pagebreak()

= Forcing block-level inside a show rule

#show heading: it => it.body
= Inline-looking heading
Normal text follows.

#show heading: it => block(it.body)
= Block-promoted heading
Normal text follows on a new line.

#pagebreak()

= breakable: false (jump to own page if needed)

#set page(height: 80pt)
The following block jumps to its own page if it doesn't fit.
#block(breakable: false, lorem(15))

#set page(height: auto)

= Sticky: stay attached to the next block

#show heading: set block(sticky: true)   // default
#lorem(20)

= Heading that won't be orphaned at page bottom
#lorem(10)
