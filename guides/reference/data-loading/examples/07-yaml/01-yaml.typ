#set page(width: 14cm, height: auto, margin: 1cm)

== Bookshelf from YAML

#let shelf = yaml("_assets/scifi.yaml")

#for (author, works) in shelf [
  *#author*
  #for w in works [
    - #w.title (#w.published)
  ]
]

== Encode round-trip

#let payload = (
  flag: true,
  count: 7,
  items: ("a", "b"),
  nested: (key: "value"),
)
#let s = yaml.encode(payload)
Encoded YAML:

#raw(s, lang: "yaml", block: true)

Round-trip equal: #(yaml(bytes(s)) == payload)
