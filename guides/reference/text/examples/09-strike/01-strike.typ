// 'strike(body, stroke: auto, offset: auto, extent: 0pt, background: false)'
// draws a line THROUGH text. NOT 'evade' field -- a strikethrough always
// crosses everything.
//
// IMPORTANT: this is VISUAL ONLY. Strikethrough text remains in the document
// and can be selected / copied. Don't use this for real redaction of
// sensitive content.

= Default

This is #strike[not] relevant.

= Custom stroke (color + thickness)

This is #strike(stroke: 1.5pt + red)[very stricken through]. \
This is #strike(stroke: 10pt)[redacted-looking but NOT redacted]. \

= Offset

This is #strike(offset: auto)[low-ish] (font-defined). \
This is #strike(offset: -3.5pt)[on-top].

= 'extent' to skip / extend the strike

This #strike(extent: -2pt)[skips] parts of the word. \
This #strike(extent: 2pt)[extends] beyond the word.

= 'background: true' (line behind glyphs) -- visible only with thick stroke

#set strike(stroke: red)
#strike(background: true)[Behind glyphs] \
#strike(background: false)[In front of glyphs]
