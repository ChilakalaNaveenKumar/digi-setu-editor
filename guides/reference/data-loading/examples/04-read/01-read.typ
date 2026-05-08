#set page(width: 14cm, height: auto, margin: 1cm)

== Reading text and showing it as raw

#let note = read("_assets/note.txt")
Length: #note.len() characters \

#raw(note, block: true, lang: "text")

== Reading bytes (encoding: none)

#let raw-bytes = read("_assets/note.txt", encoding: none)
Bytes length: #raw-bytes.len() \
First 8 bytes: #repr(raw-bytes.slice(0, 8))

== Pipelining: text → JSON

#let inline = "{\"hello\": \"world\", \"n\": 3}"
#let parsed = json(bytes(inline))
Parsed: #parsed.hello (n=#parsed.n)
