# `upper` — convert to uppercase

`upper(text: str | content) -> str | content`

Mirror image of `lower`. Returns a Unicode-correct uppercase version of the input. Return type matches input type (`str` → `str`, `content` → `content` with formatting preserved).

```typst
#upper("abc")            // "ABC"
#upper[*my text*]        // *MY TEXT*
```

## German `ß` and full case folding

`upper("ß")` returns `"SS"` (Unicode-default full case folding). If you want the recently-added `ẞ` (capital sharp S, U+1E9E), insert it as a literal character — `upper` won't produce it.

## Common patterns

```typst
// All-caps headings
#show heading: it => upper(it.body)

// All-caps in a small region
#text(tracking: 0.05em)[#upper[Section title]]
```

When using all-caps for small caps-like effects, also bump `tracking` slightly — uppercase letters look cramped without it.

## Pitfalls

- **No locale parameter.** Uppercasing is Unicode-default. Turkish `i` → `İ` mapping is NOT applied — it stays `I`. For locale-correct casing, do it before Typst.
- **`upper("ß")` is `"SS"`, not `"ẞ"`.** This catches anyone expecting strict round-tripping with `lower`.
- **Content input preserves formatting.** `upper[*bold*]` returns bold uppercase content. To get a plain string, pass a string.
- **Raw blocks are not case-folded.** `` upper[`code`] `` keeps `code` lowercase (intentional — code shouldn't be modified).
- **Math expressions pass through unchanged.** `upper($abc$)` returns the math element as-is.
- **Lossy round-trip.** `lower(upper(x))` is not always equal to `lower(x)` (because of `ß` → `SS` and similar mappings).

## Examples (compile-verified)

- `examples/14-upper/01-upper.typ` — string vs content input, `ß` → `SS` mapping, formatting preservation, all-caps heading show rule.

## Reference

- Official: https://typst.app/docs/reference/text/upper/
- `lower`: https://typst.app/docs/reference/text/lower/
- `smallcaps`: https://typst.app/docs/reference/text/smallcaps/
