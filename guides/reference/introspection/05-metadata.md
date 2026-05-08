# `metadata()` — Invisible Queryable Values

`metadata` lets you embed any value into the document **without producing
visible output**, and look it up later via `query` or the
`typst query` CLI.

## Signature

```text
metadata(value: any) -> content
```

The result is content with no visible rendering. Attach a `<label>` to
identify the metadata you want to retrieve.

## Two main use cases

### 1. In-document programmatic queries

```typst
#metadata("draft") <doc-status>

#context {
  let status = query(<doc-status>).first().value
  if status == "draft" [
    #set text(fill: red)
    [DRAFT — do not distribute]
  ]
}
```

You can store strings, numbers, dictionaries, arrays — anything Typst
can hold.

### 2. Exposing values to the CLI (`typst query`)

```text
$ typst query example.typ "<doc-status>"
[
  { "func": "metadata", "value": "draft", "label": "<doc-status>" }
]

$ typst query example.typ "<doc-status>" --field value --one
"draft"
```

This is great for build pipelines that need to read structured data out
of `.typ` files (titles, version stamps, author lists). See the
[`query` page](./06-query.md#command-line-queries) for full CLI details.

## Reading metadata back

```typst
#context {
  let m = query(<my-data>)
  for item in m {
    [- #item.value \ ]
  }
}
```

Each metadata element appears in the query result as content with a
`.value` field — the exact value you embedded.

## Tips

- Use multiple metadata elements with the same label to collect a list of
  values.
- Wrap structured data in dictionaries: `metadata((title: ..., author: ...))`.
- For values you want to *display* later (not just to programs), prefer
  `state` so you can read the value via `state(...).get()` directly.
