// Unicode helpers:
//   "x".to-unicode()      -> int  (codepoint of a SINGLE character)
//   str.from-unicode(n)   -> str  (single-character string for codepoint n)
//
// .normalize(form: "nfc"|"nfd"|"nfkc"|"nfkd") returns a normalized copy.
//   nfc   composed form: 'é' is 1 codepoint U+00E9.
//   nfd   decomposed:    'e' + combining acute (U+0065 U+0301) -- 2 codepoints.
//   nfkc  like NFC plus Unicode COMPATIBILITY decomposition (e.g. 'ﬁ' -> 'fi').
//   nfkd  like NFD plus compatibility decomposition.
//
// Reach for normalize() before equality / search / sort on user input that
// may mix decomposed and composed forms (typed accents, IME output, etc.).

"a".to-unicode():        #"a".to-unicode()
str.from-unicode(97):    #str.from-unicode(97)

// Map codepoints of a string back to ints.
codepoints of "a\u{0300}":
  #("a\u{0300}".codepoints().map(str.to-unicode))

// Normalization round-trip.
NFC vs NFD of "é":
  #(repr("é".normalize(form: "nfc"))) vs
  #(repr("é".normalize(form: "nfd")))

NFKC of fi-ligature "\u{FB01}":
  #("\u{FB01}".normalize(form: "nfkc"))
