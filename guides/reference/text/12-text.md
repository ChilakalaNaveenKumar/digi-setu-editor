# `text` — the master text styling element

`text(body: content, ..many fields..) -> content`

The most-used element in Typst. Customizes font, size, weight, color, language, OpenType features, and dozens of other text properties. Use `#set text(...)` for ranges and `#text(...)[body]` for one-offs.

```typst
#set text(font: "Libertinus Serif", size: 11pt, lang: "en")
Body text rendered with the configured font.

#text(weight: "bold", fill: red)[Inline override]
```

## Field cheat sheet (grouped)

### Font identity

| Field      | Default                | Notes                                                               |
| ---------- | ---------------------- | ------------------------------------------------------------------- |
| `font`     | `"libertinus serif"`   | String OR priority array (`("A", "B")`) OR dict with `covers:`      |
| `fallback` | `true`                 | Last-resort search across all fonts for missing glyphs              |
| `style`    | `"normal"`             | `"normal"` / `"italic"` / `"oblique"` (italic falls back to oblique and vice versa) |
| `weight`   | `"regular"`            | 100–900 OR `"thin"`/`"extralight"`/.../`"black"`                     |
| `stretch`  | `100%`                 | 50–200%; only effective if font has condensed/expanded variants     |
| `size`     | `11pt`                 | Basis of `em` unit. Self-relative: `1.5em` is 1.5× current size      |

### Color & spacing

| Field             | Default            | Notes                                              |
| ----------------- | ------------------ | -------------------------------------------------- |
| `fill`            | `luma(0%)` (black) | Color / gradient / tiling                           |
| `stroke`          | `none`             | Glyph outline (any stroke value)                    |
| `tracking`        | `0pt`              | Extra space BETWEEN characters                      |
| `spacing`         | `100% + 0pt`       | Word-space scale (relative length)                   |
| `cjk-latin-spacing` | `auto`           | Auto inserts space at CJK-Latin boundaries          |
| `baseline`        | `0pt`              | Vertical shift (positive = down)                     |
| `overhang`        | `true`             | Allow hanging punctuation in justified text          |

### Layout edges

| Field         | Default          | Effect                                               |
| ------------- | ---------------- | ---------------------------------------------------- |
| `top-edge`    | `"cap-height"`   | Where containers consider the top of the text       |
| `bottom-edge` | `"baseline"`     | Where containers consider the bottom of the text    |

### Localization

| Field    | Default | Notes                                                                                        |
| -------- | ------- | -------------------------------------------------------------------------------------------- |
| `lang`   | `"en"`  | ISO 639. Affects hyphenation, smart quotes, smallcaps, accessibility metadata                 |
| `region` | `none`  | ISO 3166-1 alpha-2 (e.g. `"GB"`, `"US"`)                                                      |
| `script` | `auto`  | OpenType writing script tag                                                                    |
| `dir`    | `auto`  | `ltr` / `rtl` / `auto` (inferred from `lang`)                                                  |

### Hyphenation & line-break costs

| Field        | Default | Notes                                                                            |
| ------------ | ------- | -------------------------------------------------------------------------------- |
| `hyphenate`  | `auto`  | Enabled iff `par.justify` is on. Forced on/off via `true`/`false`                 |
| `costs`      | dict    | `(hyphenation: 100%, runt: 100%, widow: 100%, orphan: 100%)`. Higher = avoid more |

### OpenType features

| Field                        | Default     | Toggles                                          |
| ---------------------------- | ----------- | ------------------------------------------------ |
| `kerning`                    | `true`      | `kern`                                           |
| `alternates`                 | `false`     | `salt`                                           |
| `stylistic-set`              | `()`        | `ss01`–`ss20` (int or array of ints)             |
| `ligatures`                  | `true`      | `liga`, `clig`                                   |
| `discretionary-ligatures`    | `false`     | `dlig`                                           |
| `historical-ligatures`       | `false`     | `hlig`                                           |
| `number-type`                | `auto`      | `lnum` / `onum` (lining vs old-style)            |
| `number-width`               | `auto`      | `pnum` / `tnum` (proportional vs tabular)        |
| `slashed-zero`               | `false`     | `zero`                                           |
| `fractions`                  | `false`     | `frac` — **don't** enable globally                |
| `features`                   | `(:)`       | Raw escape hatch: array of feature names OR dict |

### Body content

| Field  | Notes                                                |
| ------ | ---------------------------------------------------- |
| `body` | Content (the styled portion when called as a function) |
| `text` | Plain string (when constructed positionally with a string) |

## `set` rule vs function call

```typst
#set text(weight: "bold")          // applies until end of scope
This whole paragraph is bold.

#text(weight: "regular")[Inline override]
```

The set rule is preferred for ranges; the function call is necessary when passing styled text as an argument (`#emph(text(blue)[hello])`).

## Per-codepoint font selection

`font:` accepts a priority list where each entry can be a dict with `covers:`:

```typst
#set text(font: (
  (name: "DejaVu Sans Mono", covers: regex("[0-9]")),
  "Libertinus Serif",
))
The number 12345 is monospace; the rest is serif.
```

`covers:` accepts:
- A regex matching exactly one character class (`[a-z]`, `[0-9]`, `\d`, etc.)
- The string `"latin-in-cjk"` (for mixed CJK + Latin documents)

## Layout edges (sizing implications)

`top-edge` / `bottom-edge` change the **conceptual frame**, not the glyph rendering. They affect how containers (`rect`, `block`, `box`) size around text:

| Combination                               | Visual effect                                       |
| ----------------------------------------- | ---------------------------------------------------- |
| `top: "cap-height"`, `bottom: "baseline"` | (default) Tight to caps; descenders dangle below     |
| `top: "ascender"`, `bottom: "descender"`  | Full font box — biggest, includes diacritic room     |
| `top: "x-height"`, `bottom: "baseline"`   | Tight to lowercase body — shortest                    |
| `top: "bounds"`, `bottom: "bounds"`       | Tight to actual glyph extents                          |

## Pitfalls

- **`size: 0.8em` is RELATIVE to the previous size.** Two nested `set text(size: 0.8em)` rules give 64% of the original.
- **`fallback: false` is silent on missing glyphs** — you get "tofu" boxes (`□`). No warning yet. Combine with explicit font selection only when you've checked coverage.
- **Setting `lang: "..."` matters for accessibility, not just hyphenation.** Screen readers pick voices based on language. Always set `lang` for non-English documents.
- **`hyphenate: auto`** doesn't hyphenate ragged-right text. To hyphenate without justifying, pass `hyphenate: true` explicitly.
- **`fractions: true` globally** turns every `12/34` into a fraction glyph, including URL slashes. Use it locally inside `#text(fractions: true)[1/2]`.
- **`stretch:` only works on fonts with condensed/expanded variants.** Most fonts only have one width — `stretch` is a no-op for them.
- **`tracking` adds space, `spacing` scales space.** Easy to confuse: `tracking: 1pt` adds 1pt between every two chars; `spacing: 200%` doubles word gaps.
- **`features:` is the escape hatch for OpenType features** Typst doesn't expose by name. Use sparingly — Typst's named fields are clearer.
- **`top-edge` / `bottom-edge` defaults are tuned for prose**, not centered titles in a fixed-height box. If you center text vertically and it looks too high, change `bottom-edge` to `"descender"`.

## Examples (compile-verified)

- `examples/12-text/01-font-and-size.typ` — font priority list, style/weight/size, fill/stroke/tracking, per-codepoint `covers:` regex.
- `examples/12-text/02-language-hyphenation-direction.typ` — German with hyphenation, RTL Arabic with `dir: rtl`, `costs.hyphenation` discouraging hyphenation, `region` set.
- `examples/12-text/03-opentype-features.typ` — kerning, stylistic alternates, lining/old-style numbers, tabular vs proportional widths, slashed zero, fractions (local only), raw `features` array & dict.
- `examples/12-text/04-set-vs-call-and-edges.typ` — `#set` vs `#text()` form, `top-edge` / `bottom-edge` container sizing comparison, `baseline` shift.

## Reference

- Official: https://typst.app/docs/reference/text/text/
- ISO 639 language codes: https://en.wikipedia.org/wiki/ISO_639
- ISO 3166-1 region codes: https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2
- OpenType feature registry: https://learn.microsoft.com/en-us/typography/opentype/spec/featurelist
- `par` (justification, leading): https://typst.app/docs/reference/model/par/
- `emph`, `strong` (semantic emphasis on top of `text`): https://typst.app/docs/reference/model/emph/
