# `smallcaps` — small capitals

`smallcaps(body: content, all: bool = false) -> content`

Renders text in small capitals via OpenType font features.

```typst
#smallcaps[Hello]
```

## Parameters

| Field | Default | OpenType feature | Effect                                               |
| ----- | ------- | ---------------- | ---------------------------------------------------- |
| `all` | `false` | `smcp`           | Lowercase letters → small capitals                   |
| `all` | `true`  | `smcp` + `c2sc`  | Both lowercase AND existing uppercase → small caps   |

The default (`smcp` only) keeps uppercase letters at full size, which is the typographically correct behaviour for prose. Use `all: true` for acronyms (`UNICEF`, `UN`) so the existing capitals shrink to match the surrounding small caps.

## Font requirement

Small caps come from the font, not from synthesis. If the font doesn't ship `smcp`/`c2sc` features, **nothing changes**. Workarounds:

1. Switch to a font that has them (e.g. `Latin Modern Roman Caps`):

   ```typst
   #show smallcaps: set text(font: "Latin Modern Roman Caps")
   ```

2. Wait — Typst plans to add synthesis (faux small caps from regular caps), but it's not implemented yet.

## Common heading pattern

Replace bold-numbered headings with centered, non-bold small caps for a classical look:

```typst
#set heading(numbering: "I.")
#show heading: smallcaps
#show heading: set align(center)
#show heading: set text(weight: "regular")
```

## Pitfalls

- **No visible change in fonts without `smcp`.** This is silent — there's no warning. Test with a known-supporting font (Latin Modern, Libertinus Serif, IBM Plex Serif) if you're unsure.
- **`all: true` only matters when the body has uppercase letters already.** For all-lowercase input, `all: false` and `all: true` look identical.
- **Synthesized smallcaps are NOT yet supported.** A future Typst version will fall back to scaled-down regular caps; for now, missing-feature fonts produce regular text.
- **Numbers and punctuation** are usually unaffected. If you want lowercase numerals (old-style figures), enable `text(number-type: "old-style")`.
- **Smallcaps don't combine with `text(features:)` automatically.** If you've manually disabled `smcp` via `set text(features: (smcp: 0))`, `smallcaps[...]` won't override it without a fresh `text` call.

## Examples (compile-verified)

- `examples/07-smallcaps/01-smallcaps.typ` — default vs `all: true` (UNICEF/UN demo), classical heading style with show rules.

## Reference

- Official: https://typst.app/docs/reference/text/smallcaps/
- OpenType `smcp` / `c2sc`: https://learn.microsoft.com/en-us/typography/opentype/spec/features_pt#smcp
- `text` (font selection, features): https://typst.app/docs/reference/text/text/
