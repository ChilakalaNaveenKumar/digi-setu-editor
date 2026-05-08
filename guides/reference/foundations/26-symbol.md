# `symbol` — Unicode glyphs with named modifiers

A `symbol` is a Unicode glyph value with optional named **variants**. You access variants with chained dot syntax. Order of modifiers doesn't matter — Typst picks the variant whose modifier set is the smallest superset of the requested ones.

## Where built-in symbols live

| Module   | Contents                                            | Math-mode shorthand |
| -------- | --------------------------------------------------- | ------------------- |
| `sym`    | arrows, math operators, punctuation, currencies, …  | drop the `sym.` prefix in `$ ... $` |
| `emoji`  | every standard emoji                                | (none)              |

```typst
#sym.arrow.r           // →
#sym.gt.eq.not         // ≱
$ a gt.eq.not b $      // same symbol, math-mode shorthand
#emoji.face.halo       // 😇

// Modifier order is irrelevant.
#sym.arrow.r.long      // ⟶
#sym.arrow.long.r      // same glyph
```

Browse the full lists at the official `sym` and `emoji` module pages — they're searchable visually.

## Custom symbols

`symbol(...variants) -> symbol`

Each `variant` is either:

- a single `str` — the **modifier-less** default
- an array `(modifiers, glyph)` where `modifiers` is a dot-separated string of modifier names and `glyph` is the displayed string

```typst
#let envelope = symbol(
  "🖂",                      // default
  ("stamped",     "🖃"),
  ("stamped.pen", "🖆"),
  ("lightning",   "🖄"),
  ("fly",         "🖅"),
)

#envelope.stamped.pen   // -> 🖆
```

Resolution: `envelope.stamped.pen` matches `("stamped.pen", ...)` because `{stamped, pen}` is a superset of itself with no extras. If multiple variants tie, the one with the fewest extra modifiers wins.

## Pitfalls

- **Math-mode shorthand only drops `sym.`** — `emoji.*` always needs the prefix, even in math mode.
- **Modifiers are SETS, not paths.** `arrow.r.long` and `arrow.long.r` resolve to the same variant. There is no ordering meaning.
- **A required modifier without a matching variant errors.** `envelope.unknown` is a compile error if no variant has the `unknown` modifier.
- **Custom symbols are values, not module entries.** You can't `#import` from a custom symbol. To group several symbols, expose them via your own module file.
- **Visual variants depend on the font.** A symbol may render with different shapes across fonts; for fixed visuals use `image` or pre-rasterized assets.

## Examples (compile-verified)

- `examples/26-symbol/01-builtin-symbols.typ` — `sym.arrow.r`, `sym.gt.eq.not`, math-mode shorthand, `emoji.face.halo`, modifier-order independence.
- `examples/26-symbol/02-custom-symbol.typ` — `symbol("🖂", ("stamped", "🖃"), ("stamped.pen", "🖆"), …)` and accessing each variant.

## Reference

- Official: https://typst.app/docs/reference/foundations/symbol/
- Built-in `sym` module: https://typst.app/docs/reference/symbols/sym/
- Built-in `emoji` module: https://typst.app/docs/reference/symbols/emoji/
