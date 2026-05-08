# `query()` — Find Elements in the Document

`query` is the workhorse of introspection. Given a selector, it returns
**every** locatable element matching it, in document order, as content.

## Signature

```text
query(target: label | selector | location | function) -> array<content>
```

`query` is **contextual**.

## What you can pass as `target`

| Form                                              | Meaning                                          |
| ------------------------------------------------- | ------------------------------------------------ |
| An element function (`heading`, `figure`)         | Every element of that type.                      |
| A label (`<intro>`)                               | Every element carrying that label.               |
| A `where` selector (`heading.where(level: 1)`)    | Element type filtered by field value.            |
| A combined selector (`selector(heading).before(here())`) | Adds anchored or set operations.          |

Only **locatable** element types can be queried (see the
[overview](./00-introspection-overview.md#locatable-elements)).

## Working with results

`query` returns an array of content — the same content objects Typst will
render. Each item supports:

- `e.fields()` — dictionary of all the element's fields.
- `e.body` (and any other field, e.g. `e.level` for headings).
- `e.location()` — the element's `location`.
- `e.func()` — the element's function (e.g. `heading`).

## Recipe: a custom table of contents

```typst
#context {
  let chapters = query(heading.where(level: 1, outlined: true))
  for c in chapters {
    let loc = c.location()
    let nr  = numbering(loc.page-numbering(),
                        ..counter(page).at(loc))
    [#c.body #h(1fr) #nr \ ]
  }
}
```

This is essentially what the built-in `outline` does — and is the right
shape for any "list of figures", "list of equations", "index" you want to
build by hand.

## Recipe: count headings before the current point

```typst
#context [
  Headings so far: #query(
    selector(heading).before(here())
  ).len()
]
```

`selector(...).before(loc)` and `.after(loc)` come from the
[`selector`](../foundations/19-selector.md) type.

## Pitfalls and performance

- **Self-referential queries.** If your query produces or removes
  elements that would change the query's result, Typst gives up after a
  few iterations. Don't write content that depends on the count of
  itself.
- **Repeated queries.** `query` walks the whole document. If you need
  the result in many places (e.g. a page header), capture it once in a
  `let` outside the show rule.
- **Style-only filters.** A `where(...)` selector matches *fields set on
  the element*, not values inherited from `set` rules.

## Command-line queries

The `typst query` CLI executes a single query against a document and
returns serialized JSON.

```text
$ typst query example.typ "<note>"
[ { "func": "metadata", "value": "...", "label": "<note>" } ]

$ typst query example.typ "<note>" --field value --one
"..."

$ typst query example.typ "heading.where(level: 1)" --field body
[...]
```

Useful flags:

| Flag                         | Meaning                                                |
| ---------------------------- | ------------------------------------------------------ |
| `--field NAME`               | Project to one field per element.                      |
| `--one`                      | Return a scalar instead of an array (errors if not exactly one). |
| `--target paged` / `--target html` | Query against a specific export target.          |

This is the canonical way to extract structured data (titles, authors,
build flags) from `.typ` files in a build pipeline.
