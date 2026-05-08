// 'emoji' is a module of named emoji glyphs. In MARKUP, prefix with
// '#emoji.':
//   #emoji.face.cry      -> 😢
//   #emoji.heart.blue    -> 💙
//   #emoji.cat           -> 🐈
//
// Like 'sym', emoji uses dot-modifiers for variants:
//   .blue, .green, .pink, .purple, ...           color variant
//   .smile, .cry, .angry, .kiss, ...             facial mood
//   .l, .r, .t, .b                               direction
//
// FONT REQUIREMENT: emoji glyphs need an emoji font installed (Apple
// Color Emoji on macOS, Segoe UI Emoji on Windows, Noto Color Emoji on
// Linux). If your font does NOT contain a glyph, you'll see a tofu box.
//
// Discoverability: many names are NOT what you might guess (e.g. the
// red heart is just 'heart', not 'heart.red'). Browse the official list
// at https://typst.app/docs/reference/symbols/emoji/ when in doubt.

= Faces

#emoji.face.smile quad #emoji.face.cry quad #emoji.face.angry quad
#emoji.face.cool quad #emoji.face.kiss quad #emoji.face.think

= Hearts (no .red -- plain 'heart' is the red one)

#emoji.heart quad #emoji.heart.blue quad #emoji.heart.green quad
#emoji.heart.purple quad #emoji.heart.broken quad #emoji.heart.beat

= Animals

#emoji.cat quad #emoji.dog quad #emoji.lion quad #emoji.tiger quad
#emoji.elephant quad #emoji.unicorn quad #emoji.rocket quad #emoji.alien

= Hands

#emoji.hand.ok quad #emoji.hand.peace quad #emoji.hand.r quad
#emoji.hand.l quad #emoji.hand.wave quad #emoji.hand.write

= Inline use

A celebration #emoji.party merits great food #emoji.face.smile and
plenty of #emoji.coffee #emoji.fire.

The tomato #emoji.tomato is a fruit #emoji.face.think.
