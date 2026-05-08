# `locate()` — Find a Single Element's Location

`locate(selector)` returns the [`location`](./04-location.md) of the
**unique** element matching the selector. If zero or more than one element
matches, you get an error — make the selector specific (usually with a
label).

## Signature

```text
locate(selector: label | selector | location | function) -> location
```

`locate` is **contextual**.

## Typical workflow

```typst
#context [
  "Introduction" starts on page #locate(<intro>).page().
]

= Introduction <intro>
```

Equivalently for first-of-many lookups:

```typst
#context [
  First heading is on page
  #query(heading).first().location().page()
]
```

`locate(...)` is the right choice when you can guarantee the selector
matches exactly one element (typically a labelled element). For "first /
all" lookups use [`query`](./06-query.md).

## When to use which

| Want                                 | Reach for                                    |
| ------------------------------------ | -------------------------------------------- |
| The location of *one* labelled thing | `locate(<label>)`                            |
| First/last of a kind                 | `query(...).first().location()`              |
| Every match                          | `query(...).map(e => e.location())`          |
| The current spot                     | `here()`                                     |

## Tips

- Combine with `counter(...).at(loc)` to read a counter at a specific
  point in the document — the foundation of "X / Y" cross-references.
- `locate` is contextual, so wrap it (or any `.page()`/`.position()` call
  on its result) in `#context [...]`.
