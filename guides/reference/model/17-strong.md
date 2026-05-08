# `strong` — bold emphasis (weight delta)

`strong(body, delta: int = 300) -> content`

Increases the current font weight by `delta`. **`delta` is an INCREMENT, not an absolute weight** — passing `delta: 300` to text already at weight 400 ("regular") gets you weight 700 ("bold").

## Markup shorthand

Wrap content in asterisks: `*text*`. Same word-boundary rule as `emph`:

```typst
*works at boundaries*
ex#strong[trao]rdinary   // mid-word: must use the function
```

## `delta`

| `delta` | Effective weight if base is 400 | Notes                              |
| ------- | -------------------------------- | ---------------------------------- |
| `300`   | 700 (bold)                       | default                            |
| `0`     | 400                              | strong element exists but invisible — useful when only show rules / queries should care |
| `100`   | 500 (medium)                     | subtle emphasis                    |
| `600`   | 1000 (capped at font max)        | ultra-bold if font supports it     |

Set globally with `#set strong(delta: ...)`.

## Show rules

```typst
#show strong: set text(fill: red)
*Strong is now red AND bold.*

#show strong: it => text(fill: red, it.body)
// Identical effect (weight stays bold), but the handler form lets you
// rebuild the content from scratch if you need to.
```

## Pitfalls

- **`delta`, not absolute.** `set strong(delta: 700)` does NOT mean "use weight 700". It means "add 700 to whatever the current weight is". For absolute control use `text(weight: 700, ...)`.
- **Weights are clamped to the font's available range.** A font that ships only Regular + Bold can't do `delta: 600` or weight 1000 — it picks the nearest available face.
- **Word-boundary shorthand silently fails** mid-word — same trap as emph.
- **`set strong(delta: 0)` doesn't remove the element.** Show rules and `query(strong)` still find it. To truly skip styling, don't wrap in `*...*` at all.

## Examples (compile-verified)

- `examples/17-strong/01-strong-syntax-and-delta.typ` — `*..*` shorthand, `#strong[...]` function, partial-word case, show rule, `delta: 0` (no visual effect), `delta: 600` (ultra-bold attempt).

## Reference

- Official: https://typst.app/docs/reference/model/strong/
- `text(weight: ...)` (absolute weight): https://typst.app/docs/reference/text/text/
