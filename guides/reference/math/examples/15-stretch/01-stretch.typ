// 'stretch(body, size: 100% + 0pt)' stretches a glyph to a given size,
// most commonly to make a base wide enough to hold its top and bottom
// attachments.
//
// Only some glyphs are stretchable; this depends on the math font.
// Most fonts agree on the common ones (arrows, equals, brackets, etc).

= Wide arrow with annotation above

$ H stretch(=)^"define" U + p V $

$ f : X stretch(->>, size: #150%)_"surjective" Y $

= Wide harpoon and bracket

$ x stretch(harpoons.ltrb, size: #3em) y $

$ stretch(\[, size: #150%) z $

= 'stretch' is mostly used with attachments

The base of `_`/`^` attachments only stretches when wrapped in
`stretch()`. Compare:

$ X overline(->) Y quad
  X stretch(->) Y quad
  X stretch(->, size: #200%)_"big" Y $
