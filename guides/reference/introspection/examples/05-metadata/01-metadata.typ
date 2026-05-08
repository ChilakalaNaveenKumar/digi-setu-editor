#set page(width: 14cm, height: auto, margin: 1cm)

#metadata("draft") <doc-status>
#metadata((title: "Demo Doc", version: "0.2.0")) <doc-info>

#metadata("first") <todo>
Some text.
#metadata("second") <todo>
More text.
#metadata("third") <todo>

== Reading single labelled metadata

#context {
  let info = query(<doc-info>).first().value
  [Title: *#info.title*, version: #info.version]
}

== Branching on a status flag

#context {
  let status = query(<doc-status>).first().value
  if status == "draft" {
    set text(fill: red)
    [Draft watermark would go here.]
  } else [
    Document is ready.
  ]
}

== Collecting all matching metadata into a list

#context {
  let items = query(<todo>).map(m => m.value)
  [TODOs: #items.join(", ")]
}
