// 'sub(body, typographic: true, baseline: auto, size: auto)' renders text
// in subscript.
//
// 'typographic: true' (default) tries to use the font's dedicated subscript
// glyphs ('subs' OpenType feature). If the font lacks them OR you set
// 'typographic: false', Typst SYNTHESIZES subscripts by lowering and
// scaling regular glyphs.
//
// For SYNTHESIZED subscripts only (typographic: false OR font lacks subs):
//   baseline   downward shift (auto = font metric, fallback 0.2em)
//   size       glyph size (auto = font metric, fallback 0.6em)

= Markup-style call

H#sub[2]O \
Revenue#sub[yearly] \
log#sub[2] of n

= Typographic vs synthesized

Typographic (uses font's subs glyphs if available):
N#sub(typographic: true)[1]

Synthesized (always lowers + scales regular glyphs):
N#sub(typographic: false)[1]

= Custom synthesized metrics (only effective when synthesized)

Default:           N#sub(typographic: false)[1] \
baseline 0.4em:    N#sub(typographic: false, baseline: 0.4em)[1] \
size 0.5em:        N#sub(typographic: false, size: 0.5em)[1]
