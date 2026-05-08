# `smartquote` — language-aware auto quotes

`smartquote(double: bool = true, enabled: bool = true, alternative: bool = false, quotes: auto | str | array | dictionary = auto) -> content`

Replaces typed `'` and `"` with the correct opening/closing quote glyphs for the active `text.lang`. **You almost never call this directly** — typing the quote character in markup creates a `smartquote` element automatically.

```typst
"Hello," she said.   // -> "Hello," with curly English quotes
```

## How it picks the glyph

1. Looks at `text.lang` (set via `#set text(lang: "...")`).
2. Looks at `double` (true for `"`, false for `'`).
3. Infers open vs close from context (what's around it).
4. Optionally consults `alternative` for languages with two quote conventions.
5. Falls back to defaults if `quotes` was overridden.

## Disabling smartness

| Scope          | How                                                  |
| -------------- | ---------------------------------------------------- |
| One quote      | Escape: `\"`, `\'`                                   |
| Globally       | `#set smartquote(enabled: false)`                    |
| Until reset    | Re-enable with `#set smartquote(enabled: true)`      |

## `alternative`

Some languages (e.g. German, French) have an alternative quote convention. `#set smartquote(alternative: true)` switches to it. No-op for languages without an alternative set.

## Custom quote characters

`quotes:` accepts:

| Type         | Shape                                                  | What it sets                            |
| ------------ | ------------------------------------------------------ | --------------------------------------- |
| `str` (2 chars) | `"<>"`                                              | Opening + closing for **double** quotes |
| `array` (2 elements) | `("[", "]")`                                  | Same as above                           |
| `dictionary` | `(double: ?, single: ?)` — each `auto`/str/array  | Both single and double                  |

```typst
#set smartquote(quotes: "()")        // " becomes ( and )
#set smartquote(quotes: (
  single: ("[[", "]]"),
  double: auto,
))
```

## Pitfalls

- **`#set text(lang: ...)` must come BEFORE the quoted text** for the language-correct glyphs to render. Switching `lang` later doesn't retro-apply to earlier quotes.
- **Apostrophes are `'` (smartquote single).** This is fine for most prose but can be wrong for code-like text — use raw blocks or escape: `it\'s`.
- **Smart quotes inside raw blocks aren't replaced.** `` `'foo'` `` keeps straight quotes (intentional — code shouldn't be modified).
- **Math mode treats `'` as the prime symbol.** `$f'(x)$` is `f-prime`, not `f-smartquote`.
- **`quotes: "[[]]"` doesn't work directly** — strings need to be 2 grapheme clusters total. To use multi-char quotes, use the array or dict form.
- **`quote` element ≠ `smartquote`.** `quote` is the explicit quotation block element with optional attribution; `smartquote` is the typing-shortcut auto-replacement.

## Examples (compile-verified)

- `examples/08-smartquote/01-smartquote.typ` — English / German / French defaults, `enabled: false` global + `\"` per-quote escape, `alternative: true` for German, custom `quotes: "()"` and dict-form `single`/`double`.

## Reference

- Official: https://typst.app/docs/reference/text/smartquote/
- `text.lang`: https://typst.app/docs/reference/text/text/#parameters-lang
- `quote` (the citation block element): https://typst.app/docs/reference/model/quote/
