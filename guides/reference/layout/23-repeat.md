# `repeat(body, gap: 0pt, justify: true)` — fill space with repeated content

Repeats `body` to fill the available space. Common uses: dot-leader fills, custom outline entries, index leaders.

**Errors** if the available space is unbounded (would generate infinite content). Always wrap in a `box(width: 1fr, ...)` or similar bounded container.

## Parameters

| Param    | Type      | Default  | Notes                                                              |
| -------- | --------- | -------- | ------------------------------------------------------------------ |
| `body`   | content    | required | The content to repeat.                                              |
| `gap`    | length     | `0pt`     | Gap between successive copies.                                      |
| `justify` | bool      | `true`    | If `true`, expand the gap so copies span the full available width. |

## Common patterns

```typst
// Dotted leader for a signature line
Sign here: #box(width: 1fr, repeat[.])

// Index entry
Chapter 1 #box(width: 1fr, repeat[ . ]) 23

// Custom outline entry leader (replace dotted leader)
#show outline.entry: it => link(
  it.element.location(),
  it.indented(
    it.prefix(),
    it.body() + box(width: 1fr, repeat(gap: 2pt)[·]) + it.page(),
  ),
)
```

## Accessibility

Repeated content is automatically marked as a [PDF artifact](https://typst.app/docs/reference/pdf/artifact/) and hidden from Assistive Technology. **Do NOT** use `repeat()` for content that contributes to meaning.

## Examples (compile-verified)

- `examples/23-repeat/01-repeat.typ` — dotted leader for signatures, custom-gap index entries, `justify: false` tight fill, custom outline entry leader.

## Reference

https://typst.app/docs/reference/layout/repeat/
