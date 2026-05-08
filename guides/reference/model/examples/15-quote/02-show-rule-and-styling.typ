// Block quotes get '1em' horizontal padding by default. Adjust with show
// rules on '#show quote: ...' (or scope with 'quote.where(block: true)').
//
// To customize INLINE quotes (which by default get smart double quotes
// around the body), write a show rule that targets 'quote.where(block: false)'.

#set quote(block: true)
#show quote: set align(center)
#show quote: set pad(x: 5em)

#quote(attribution: [Gandalf])[
  You cannot pass... I am a servant of the Secret Fire, wielder of the
  flame of Anor. You cannot pass.
]

= Custom inline rendering with attribution

#show quote.where(block: false): it => {
  ["] + h(0pt, weak: true) + it.body + h(0pt, weak: true) + ["]
  if it.attribution != none [ (#it.attribution)]
}

A typical inline quote with attribution renders as
#quote(attribution: [Descartes])[cogito, ergo sum]
which uses the rule above to add the parenthesized author after the closing
quote mark.

And a longer one with an explicit link as attribution:
#quote(attribution: link("https://typst.app/home")[typst.app])[
  Compose papers faster
]
