# `selector` — pick elements out of the document

A selector describes **which elements to target**. Used with:

- `show selector: ...` rules — restyle / transform matches.
- `query(selector)` — get the array of matching elements (requires `context`).
- Built-in functions that accept a selector to filter their behavior, e.g. `outline(target: ...)`.

## Source forms (anything that "is a selector")

| Form                                  | Matches                                            |
| ------------------------------------- | -------------------------------------------------- |
| `element_function`                    | every instance of that element (e.g. `heading`)    |
| `element_function.where(field: val)`  | instances where the field equals `val`             |
| `<label>` (or `label("name")`)        | element(s) with that label                         |
| `"some text"`                         | text matching exactly                              |
| `regex("...")`                        | text matching the pattern                          |
| `location` (from `here()`, etc.)      | element at that location                           |
| `selector(any-of-the-above)`          | explicit constructor; lets you call combinators    |

A bare label or regex is *already* a selector — you usually don't need to wrap it. Wrap with `selector(...)` only when you want to chain `.or` / `.and` / `.before` / `.after` on it.

## Combinators

| Method                                 | Meaning                                                                  |
| -------------------------------------- | ------------------------------------------------------------------------ |
| `.or(other, ...)`                      | union — match this OR any of those                                       |
| `.and(other, ...)`                     | intersection — match this AND all others (rare; useful with kind+label)  |
| `.before(end, inclusive: bool = true)` | match only elements occurring before `end` in the doc                    |
| `.after(start, inclusive: bool = true)`| match only elements occurring after `start` in the doc                   |

`.before` / `.after` need a positional anchor, so they only work with selectors that resolve to specific positions (a label, a function call, another full selector). They're commonly used to scope a query to "the current chapter" or similar.

## Two canonical patterns

### 1. Restyle by selector (no `context` needed)

```typst
#show heading.where(level: 1): set text(fill: navy)
#show heading.where(level: 1).or(heading.where(level: 2)): set text(weight: "bold")
#show <hot>: it => box(fill: yellow, inset: 4pt, it)
```

Show rules **stack**: every matching rule fires for an element. Order in source determines precedence when rules conflict on the same property.

### 2. Query the document (needs `context`)

```typst
#context {
  let lvl1 = heading.where(level: 1)
  let in-intro = lvl1.before(<chapter-1>, inclusive: false)
  [Intro headings: #query(in-intro).len()]
}
```

`query` is a *late* operation — it depends on the laid-out document, hence the `context` requirement. The result is an array of matched content elements; access fields like `.body`, `.level`, `.location()`.

## Pitfalls

- **`query` outside `context`** errors with `query is only available within a context expression`.
- **`.where(...)` matches by exact field equality** — there's no partial / prefix match for fields. For text patterns, use a string or regex selector.
- **`.and` of two element-functions matches nothing** (an element has exactly one element-function). It's only meaningful when one side is a label or regex.
- **`.before(<x>)` with `inclusive: true` (default)** includes the element labeled `<x>` if it also matches the base selector — easy off-by-one source. Pass `inclusive: false` when you mean *strictly* before.
- **Show-rule selectors run on every layout pass.** Heavy regex selectors slow down compilation linearly with document size.

## Examples (compile-verified)

- `examples/23-selector/01-show-rule-combinators.typ` — `.where`, `.or`, label-based show rules; demonstrates rule stacking on the same heading.
- `examples/23-selector/02-query-with-context.typ` — `context query(...)` with `.or`, `.before(..., inclusive: false)`, explicit `selector(<label>)` constructor.

## Reference

- Official: https://typst.app/docs/reference/foundations/selector/
- Show rules: https://typst.app/docs/reference/styling/#show-rules
- `query`: https://typst.app/docs/reference/introspection/query/
