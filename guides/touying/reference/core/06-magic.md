# `magic` — Show-Rule Helpers

> Source: [src/magic.typ](https://github.com/touying-typ/touying/blob/main/src/magic.typ)

The `magic` module wraps Typst built-ins (`bibliography`, `figure`,
`heading`, …) with show-rule helpers that make them play nicely with
Touying's slide model.

## `magic.bibliography(...)`

A bibliography slide constructor that lays the references out for slide
display. Use as the body of a final references slide:

```typst
== References
#magic.bibliography(title: none)
```

Common keys (forwarded to Typst's `bibliography`):

- `title` — outline title (`none` to suppress).
- `style` — citation style (`"ieee"`, `"apa"`, etc.).
- The bibliography source must be loaded earlier with
  `bibliography("ref.bib")` or via `config-common(show-bibliography-as-footnote: bibliography(bytes(...)))`.

## `magic.bibliography-as-footnote(bibliography(..))`

Show rule that turns each `@cite-key` into a footnote rather than an
inline reference, *and* adds the bibliography itself as a final
footnote-style slide:

```typst
#show: simple-theme.with(
  config-common(show-bibliography-as-footnote: bibliography(bib)),
)
```

`bib` is a `bibliography(...)` expression (often `bibliography(bytes(
"@book{knuth, ...}"))`).

## `magic.markup-text`

Helper to coerce a text-like value to inline content. Used by
`speaker-note` for cases where the body is plain text instead of
content.

## Element overrides

`magic.typ` also installs show-rule overrides on:

- `heading` — to add invisible structural metadata used by
  `display-current-heading`.
- `figure`, `equation`, `table` — to coordinate with `frozen-counters`.
- `enum`, `list`, `terms` — to apply `nontight-list-enum-and-terms`,
  `align-list-marker-with-baseline`, `scale-list-items`.
- `pagebreak`, `colbreak`, `parbreak` — to interact with subslide splits.

Most of these are internal — you don't call them directly, but they
explain why Touying needs `#show: <theme>-theme.with(...)` (rather than
just an `#import`) to take effect.

## Pitfalls

- `magic.bibliography(...)` is **content** — embed it in a slide:
  `== References \n #magic.bibliography(title: none)`.
- `bibliography-as-footnote` is a `config-common` value, not a top-level
  show rule. The naming can be confusing.
- The element overrides only fire after `#show: <theme>-theme.with(...)`.
  Show rules placed before will not be transformed.

## See also

- [`../../faq.md`](../../faq.md) — "Bibliography and Citations" section.
- [`01-configs.md`](./01-configs.md) — `config-common(show-bibliography-as-footnote: ...)`,
  `frozen-counters`, `nontight-list-enum-and-terms`.
