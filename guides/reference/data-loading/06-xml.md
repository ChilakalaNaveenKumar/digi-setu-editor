# `xml()` — Reading XML Files

`xml` parses an XML document into a Typst tree of arrays and
dictionaries. It is read-only — there is no `xml.encode`.

## Signature

```text
xml(source: str | bytes) -> array
```

The result is an array of nodes representing the document's children at
the top level (typically just one root element). Each node is either:

| Node kind | Representation                                                   |
| --------- | ---------------------------------------------------------------- |
| Text      | A `str`.                                                         |
| Element   | A `dictionary` with keys `tag: str`, `attrs: dict<str, str>`, `children: array<node>`. |

There is no separate "comment" or "processing instruction" node — those
are stripped during parsing.

## Walking the tree

A small helper makes traversal pleasant:

```typst
#let find-child(elem, tag) = elem.children.find(
  e => type(e) == dictionary and e.tag == tag,
)

#let text-of(elem) = elem.children.first()    // first text child
```

Then template against the tree:

```typst
#let root = xml("article.xml").first()       // the <article> element
= #text-of(find-child(root, "title"))
```

## Tips

- `xml.decode(...)` is **deprecated** — pass bytes directly to `xml(...)`.
- Whitespace between elements is preserved as text nodes — filter them
  out with `e => type(e) == dictionary` when iterating children.
- Attribute values are always strings — convert with `int(...)` /
  `float(...)` if needed.
- For HTML, the [`htmlist`](https://typst.app/universe/package/htmlist)
  community package may give you a friendlier API.
