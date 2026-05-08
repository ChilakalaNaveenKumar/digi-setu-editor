# `lorem` — generate blind text

`lorem(words: int) -> content`

Returns Latin-like Lorem Ipsum content of the given word count. Use it to fill space when designing layouts before you have real content.

```typst
= Section
#lorem(30)
```

## Determinism

The sequence is **randomly chosen but deterministic**: `lorem(8)` always returns the same 8 words. This means:

- Two calls to `lorem(N)` with the same `N` produce **identical** output.
- The output is stable across compiles, so it doesn't churn page layouts between runs.

To get *different* placeholder paragraphs, vary the word count.

## Pitfalls

- **Output is not real Latin** and intentionally meaningless. Don't ship it in production documents.
- **No paragraph breaks** are produced automatically. The function returns a single content run; if you want multi-paragraph blind text, call `lorem` multiple times separated by `parbreak()` or blank lines.
- **`words` must be a non-negative int.** `lorem(0)` returns empty content; negative values error.
- **Same N → same words** can hide bugs. If you need to confirm your layout handles different content, vary the word counts (`lorem(7)`, `lorem(13)`, ...).
- **Localization.** No equivalent for non-Latin scripts is built in. Use string literals or a custom helper if you need RTL/CJK placeholder text.

## Examples (compile-verified)

- `examples/03-lorem/01-lorem.typ` — small + large counts, determinism demo, used as a `figure.caption` and inside `enum` items.

## Reference

- Official: https://typst.app/docs/reference/text/lorem/
- Latin "lorem ipsum" history: https://en.wikipedia.org/wiki/Lorem_ipsum
