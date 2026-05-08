// 'smartquote(double: true, enabled: true, alternative: false, quotes: auto)'
// is the language-aware auto-replacement for typed ' and " characters.
//
// MARKUP SHORTHAND: typing ' or " in markup AUTOMATICALLY becomes a
// smartquote element that picks the right glyph based on:
//   - 'text.lang' (e.g. en, de, fr, ru, ja, ...)
//   - position (open vs close, inferred from context)
//
// To disable smartness for ONE quote: escape it: \"
// To disable globally: #set smartquote(enabled: false)

= Default English (lang: en)

"This is in quotes." — She said 'really?' but I don't think so.

= German

#set text(lang: "de")
"Das ist in Anführungszeichen." Und 'einfach' auch.

= French

#set text(lang: "fr")
"C'est entre guillemets."

#set text(lang: "en")

= Disable smartness globally

#set smartquote(enabled: false)

These are "dumb" quotes and 'dumb single' too.

#set smartquote(enabled: true)

= Disable smartness for ONE quote (escape it)

She said \"hello\" -- those backslash-escaped quotes stay literal.

= Alternative quotes (lang-dependent)

#set text(lang: "de")
#set smartquote(alternative: false)
"Standard German" \
#set smartquote(alternative: true)
"Alternative German"

#set text(lang: "en")
#set smartquote(alternative: false)

= Custom quote characters

#set smartquote(quotes: "()")
"This is parens-wrapped"

#set smartquote(quotes: (single: ("[[", "]]"),  double: auto))
'Custom single brackets' but "double quotes are still default"

#set smartquote(quotes: auto)  // reset for downstream
