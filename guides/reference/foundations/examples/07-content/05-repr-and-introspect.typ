// 'repr(value)' returns a STRING showing the internal structure of any
// value, including content. This is the canonical way to debug what
// elements a content value is composed of when you don't have the
// web-app inspector available.

#let snippet = [
  = Title
  Some _italic_ and *bold* text.
]

#raw(repr(snippet), block: true, lang: "typc")
