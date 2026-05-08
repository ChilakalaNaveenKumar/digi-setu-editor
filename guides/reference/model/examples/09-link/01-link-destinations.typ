// 'link(dest, body)' creates a hyperlink. Destinations:
//
//   "https://..."             URL string. Auto-detected in markup -- bare
//                             "http(s)://..." text is implicitly linked.
//   "mailto:foo@bar.com"      mailto / tel scheme; body optional (defaults
//   "tel:+1234567890"         to the address/number without the scheme)
//   <label>                   internal label -- jumps to that element
//   location                  internal location (from here(), locate(), query())
//   (page: int, x: len, y: len)   absolute page-coordinate jump (1-indexed pages,
//                             coords from page top-left)
//
// 'body' is the visible content. If 'dest' is a URL string and 'body' is
// omitted, the URL itself is used as the body.
//
// Default appearance: links look like normal text. Style globally with a
// show rule.

#show link: underline

= Introduction <intro>

bare URL (auto):    https://example.com \
explicit URL:       #link("https://example.com") \
URL with body:      #link("https://example.com")[See example.com] \
mailto:             #link("mailto:hello@typst.app") \
tel:                #link("tel:+15551234567") \
label jump:         #link(<intro>)[Go to intro] \
page coords:        #link((page: 1, x: 0pt, y: 0pt))[Go to top]
