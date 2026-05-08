# `sub` — subscript

`sub(body: content, typographic: bool = true, baseline: auto | length = auto, size: auto | length = auto) -> content`

Renders text smaller and lower (e.g. `H₂O`).

```typst
H#sub[2]O
```

## How it picks subscripts

| `typographic`      | Behaviour                                                                           |
| ------------------ | ----------------------------------------------------------------------------------- |
| `true` (default)   | Use the font's `subs` OpenType glyphs if present; else **synthesize** by scaling/lowering |
| `false`            | Always synthesize (ignore `subs` glyphs even if present)                            |

Use `typographic: true` for proper typography when your font has real subscript glyphs (cleaner outlines, font-tuned position). Use `typographic: false` when you need consistent rendering across fonts that may or may not have `subs`.

## Synthesis-only knobs

`baseline` and `size` only apply when subscripts are **synthesized** — they're ignored when typographic glyphs are used.

| Field       | `auto` fallback | Notes                                            |
| ----------- | --------------- | ------------------------------------------------ |
| `baseline`  | `0.2em`         | Downward shift (positive = down for subscripts)   |
| `size`      | `0.6em`         | Glyph size                                        |

`auto` reads the font's recommended metric (with the fallback above used when the font has no metric).

## Pitfalls

- **`typographic: true` is silent when the font lacks `subs`.** It just synthesizes — there's no warning. If you want guaranteed font-glyph subscripts, switch fonts or pass `typographic: false` and tune `baseline`/`size` for visual consistency.
- **`baseline` is a downward shift.** Setting `baseline: -0.4em` *raises* the text — it'd visually become a superscript. Use `super` for that semantically.
- **Math mode is not affected by `sub`.** Inside `$...$`, subscripts are written `x_2`. Don't use `#sub[]` in math contexts.
- **Subscripts in headings render small and may collide with the line above.** Increase `par.leading` if you stack many subscript-bearing lines.
- **Numbers in subscripts** look better with `text(number-type: "lining")`. Old-style figures may sit awkwardly.

## Examples (compile-verified)

- `examples/10-sub/01-sub.typ` — chemistry/log notation, `typographic: true` vs `false` comparison, `baseline`/`size` overrides on synthesized subscripts.

## Reference

- Official: https://typst.app/docs/reference/text/sub/
- `super`: https://typst.app/docs/reference/text/super/
- OpenType `subs` feature: https://learn.microsoft.com/en-us/typography/opentype/spec/features_pt#subs
