# `quote` — inline or block quotes with attribution

`quote(body: content, block: bool = false, quotes: auto | bool = auto, attribution: none | label | content = none) -> content`

Renders a quote inline or as an indented block, optionally with surrounding quote marks and an attribution.

```typst
He said #quote[I came, I saw, I conquered].

#quote(block: true, attribution: [Caesar])[
  Veni, vidi, vici.
]
```

## Parameters

| Field         | Default  | Behaviour                                                                          |
| ------------- | -------- | ---------------------------------------------------------------------------------- |
| `block`       | `false`  | `false` = inline (text run); `true` = indented standalone block                    |
| `quotes`      | `auto`   | `true`: wrap in double quotes; `false`: don't; `auto`: yes iff `block: false`     |
| `attribution` | `none`   | Author / source; **only displayed for block quotes** by default                     |

The quote-mark glyphs come from `smartquote.quotes`, which is **language-aware** via `text(lang:)`. So `#set text(lang: "de")` produces German quote marks; `lang: "en"` produces English ones.

## Block quote defaults

Block quotes get `pad(x: 1em)` (1em horizontal padding) and the attribution is rendered after the body. Override both via show rules:

```typst
#set quote(block: true)
#show quote: set pad(x: 4em)
#show quote: set align(center)
```

## Custom inline rendering

To render the attribution for inline quotes (suppressed by default), write a show rule scoped to `quote.where(block: false)`:

```typst
#show quote.where(block: false): it => {
  ["] + h(0pt, weak: true) + it.body + h(0pt, weak: true) + ["]
  if it.attribution != none [ (#it.attribution)]
}
```

The `h(0pt, weak: true)` calls remove any incidental space between the quote marks and the body.

## Bibliography integration

`attribution:` can be a `label` pointing to a bibliography entry. Combined with `#bibliography(...)`, this produces a properly formatted citation as the attribution.

```typst
#quote(block: true, attribution: <tolkien54>)[
  ...
]
#bibliography("works.bib")
```

## Pitfalls

- **`attribution` is hidden for inline quotes by default.** Use a show rule (above) if you want it.
- **`quotes: auto`** = `true` for inline, `false` for block. Pass `true` explicitly to force quote marks on a block quote.
- **Quote-mark glyphs follow `text.lang`.** Switching languages mid-document changes the glyphs but does NOT re-render previous quotes — quotes set in `lang: "de"` keep German marks.
- **`quote(block: true)` is a block-level element.** It interrupts the surrounding paragraph; following text starts a new paragraph.
- **Don't confuse `quote` with `smartquote`.** `quote` is the explicit element with optional attribution; `smartquote` is the auto-replacement for typed `'` and `"` in text.

## Examples (compile-verified)

- `examples/15-quote/01-inline-and-block.typ` — inline auto-quotes, block default, forced `quotes: true` on block, language-aware quote glyphs.
- `examples/15-quote/02-show-rule-and-styling.typ` — `set pad`, `set align`, custom inline show rule that adds attribution.

## Reference

- Official: https://typst.app/docs/reference/model/quote/
- `smartquote` (typed `'` and `"` replacement): https://typst.app/docs/reference/text/smartquote/
- `bibliography`: https://typst.app/docs/reference/model/bibliography/
- `cite`: https://typst.app/docs/reference/model/cite/
