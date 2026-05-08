#set page(width: 14cm, height: auto, margin: 1cm)

== Encode-decode round trip in memory

#let original = (
  title: "CBOR demo",
  authors: ("Alice", "Bob"),
  count: 3,
  tags: (urgent: true, draft: false),
)

#let bytes = cbor.encode(original)
#let decoded = cbor(bytes)

Original equals decoded: #(original == decoded) \
Decoded title: *#decoded.title* \
Decoded author count: #decoded.authors.len()

== Iterating over decoded data

#for author in decoded.authors [
  - #author
]
