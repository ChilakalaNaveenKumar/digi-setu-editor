# `lower` — convert to lowercase

`lower(text: str | content) -> str | content`

Returns a Unicode-correct lowercase version of the input. **Return type matches the input type**:

| Input type | Output type |
| ---------- | ----------- |
| `str`      | `str`       |
| `content`  | `content` (formatting preserved — `[*BIG*]` → `[*big*]`) |

```typst
#lower("ABC")            // "abc"
#lower[*MY TEXT*]        // *my text*
```

## Use in pipelines and show rules

Useful when you want to programmatically downcase headings, captions, or arbitrary user input:

```typst
#show heading: it => lower(it.body)
```

Combine with `upper` and string methods (`.trim()`, `.replace()`) to build casing helpers.

## Pitfalls

- **No locale parameter.** Lowercasing follows Unicode default casing rules; Turkish dotted/dotless `İ`/`I` mappings are NOT special-cased. If you need locale-aware casing, do it in your application layer before passing to Typst.
- **`ß` does not become `ss`.** German full case folding isn't applied — `ß` stays `ß`. (Uppercase `ß` becomes `ẞ` only in some fonts; default `upper("ß")` → `"SS"` since Unicode 5.1.)
- **Content input preserves nested elements.** `lower[*BOLD*]` returns *bold lowercase content*, not the string `"bold"`. To get a plain string, pass a string in.
- **Doesn't recurse into raw blocks.** `` lower[`CODE`] `` keeps the `CODE` upright (raw text isn't case-folded). This is by design — code shouldn't be casing-modified.
- **Math mode is not affected.** `lower($X$)` returns the math element unchanged.

## Examples (compile-verified)

- `examples/04-lower/01-lower.typ` — string vs content input, formatting preservation, Unicode characters, use in a heading show rule.

## Reference

- Official: https://typst.app/docs/reference/text/lower/
- `upper`: https://typst.app/docs/reference/text/upper/
- `str` (for casing methods on strings): https://typst.app/docs/reference/foundations/str/
