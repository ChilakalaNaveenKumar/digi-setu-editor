# `super` — superscript

`super(body: content, typographic: bool = true, baseline: auto | length = auto, size: auto | length = auto) -> content`

Renders text smaller and raised (e.g. `1ˢᵗ`, `x²`). Mirror image of `sub`.

```typst
1#super[st] try
```

## How it picks superscripts

| `typographic`      | Behaviour                                                                           |
| ------------------ | ----------------------------------------------------------------------------------- |
| `true` (default)   | Use the font's `sups` OpenType glyphs if present; else **synthesize** by scaling/raising |
| `false`            | Always synthesize                                                                    |

## Synthesis-only knobs

| Field       | `auto` fallback | Notes                                                              |
| ----------- | --------------- | ------------------------------------------------------------------ |
| `baseline`  | `-0.5em`        | Downward shift — **negative raises the text**                       |
| `size`      | `0.6em`         | Glyph size                                                          |

The "downward shift" sign convention catches people: a `baseline: 0.4em` *lowers* the text. To raise, pass a negative value.

## Footnote markers use `super`

Footnote numbers are rendered through `super`, so a `#set super(...)` rule changes how footnote markers look:

```typst
#set super(typographic: false, size: 0.5em)
text.#footnote[Now the marker is smaller and synthesized.]
```

Use this to slightly enlarge or shrink markers globally without writing a custom show rule.

## Pitfalls

- **`baseline` sign is downward.** `baseline: 0.5em` for `super` *lowers* the text — it'd visually become a subscript. Use negative values to raise.
- **Set rules on `super` change footnote markers** — be deliberate. If you want the change to apply ONLY to inline `#super[]` calls but not footnote markers, scope it with `where`:
  
  ```typst
  // Affects manual super only, not footnotes:
  #show super: it => text(fill: red, it)
  ```
  
  But there's no built-in selector to distinguish "marker super" from "manual super" — you generally just live with both being affected by `set super`.
- **Math mode is not affected.** Inside `$...$`, write `x^2` for math superscripts.
- **Stacked sub/super collide**, especially when both are synthesized. Bump up `par.leading` for chemistry-heavy text.
- **`typographic: true` is silent on missing `sups`.** Switch fonts or pass `typographic: false` if appearance matters.

## Examples (compile-verified)

- `examples/11-super/01-super.typ` — ordinals, math notation, typographic vs synthesized comparison, `baseline`/`size` overrides, `set super` affecting footnote markers.

## Reference

- Official: https://typst.app/docs/reference/text/super/
- `sub`: https://typst.app/docs/reference/text/sub/
- `footnote` (uses super under the hood): https://typst.app/docs/reference/model/footnote/
- OpenType `sups` feature: https://learn.microsoft.com/en-us/typography/opentype/spec/features_pt#sups
