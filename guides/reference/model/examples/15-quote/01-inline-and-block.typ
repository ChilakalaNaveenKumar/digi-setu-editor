// 'quote(body, block: false, quotes: auto, attribution: none)' renders an
// inline or block quote with optional attribution.
//
// Fields:
//   block         bool                 inline (default) vs block
//   quotes        auto | bool          whether to add surrounding double quotes
//                                        - auto: yes for inline, no for block
//                                        - explicit override accepted
//   attribution   none | label | content   shown only for block quotes by default
//                  label form: points to a bibliography entry
//
// The actual quote-mark glyphs come from 'smartquote.quotes' which is
// language-aware (driven by 'text.lang').

= Inline quote with auto quotes

Plato is often misquoted as the author of #quote[I know that I know nothing],
which is a paraphrase of his actual longer statement.

= Block quote (no surrounding quote marks by default)

#set quote(block: true)

#quote(attribution: [Plato])[
  ... I seem, then, in just this little thing to be wiser than this man at
  any rate, that what I do not know I do not think I know either.
]

#quote(attribution: [JFK])[
  Ich bin ein Berliner.
]

= Forcing quotes on a block

#quote(block: true, quotes: true, attribution: [Anonymous])[
  Even a block quote can be wrapped in quote marks if you ask explicitly.
]

= Language-aware quote marks (auto from text.lang)

#set text(lang: "de")
Ein deutsch-sprechender Author zitiert: #quote[Ich bin ein Berliner.]

#set text(lang: "en")
And an english speaker writes: #quote[I am a Berliner.]
