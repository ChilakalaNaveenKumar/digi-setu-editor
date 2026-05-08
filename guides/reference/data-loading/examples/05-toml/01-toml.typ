#set page(width: 14cm, height: auto, margin: 1cm)

== Loading a TOML config

#let d = toml("_assets/details.toml")

= #d.title
Version: #d.version \
Authors: #d.authors.join(", ", last: " and ") \
Contact: #d.contact.email · #d.contact.phone

#table(
  columns: 2,
  [*Section*], [*Pages*],
  ..for s in d.sections {
    ([#s.name], [#s.pages])
  },
)

== Encode round-trip

#let payload = (
  enabled: true,
  retries: 3,
  hosts: ("a.example.com", "b.example.com"),
)
#let s = toml.encode(payload, pretty: false)
Encoded: \ #raw(s, lang: "toml") \

Round-trip equal: #(toml(bytes(s)) == payload)
