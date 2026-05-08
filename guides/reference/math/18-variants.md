# `math.serif` / `sans` / `frak` / `mono` / `bb` / `cal` / `scr` — math typeface variants

These functions select alternate letterforms that are encoded inside the math font (different from swapping the regular text font). All take a single `body` content arg.

## Functions

| Function       | Variant                              |
| -------------- | ------------------------------------ |
| `serif(body)`   | Roman (default)                      |
| `sans(body)`    | Sans-serif                           |
| `frak(body)`    | Fraktur                              |
| `mono(body)`    | Monospace                            |
| `bb(body)`      | Blackboard bold (double-struck)      |
| `cal(body)`     | Calligraphic (chancery)              |
| `scr(body)`     | Script (roundhand)                   |

## Blackboard bold shortcut

Uppercase Latin letters have direct symbols too: `NN`, `ZZ`, `QQ`, `RR`, `CC`, `HH` — same glyph as `bb(N)`, `bb(Z)`, etc.

## `cal` vs `scr`

These are two distinct calligraphic styles:

- `cal` — chancery / "fancy italic" capitals. Default for most fonts.
- `scr` — roundhand / "loopy" script.

How a font supports `scr`:

1. **Unicode variation sequences** — works automatically when the font has them. Few fonts do (Cambria Math, MathPSMT).
2. **Stylistic sets** — many fonts expose roundhand via `ss01` (or similar). Bridge it manually:

   ```typst
   #let scr(it) = text(stylistic-set: 1, $cal(it)$)
   ```

If the font supports neither, `scr` and `cal` look identical.

## Examples (compile-verified)

- `examples/18-variants/01-variants.typ` — side-by-side serif/sans/frak/mono, blackboard bold (`bb`), `cal` vs custom `scr` via `stylistic-set: 1`.

## Reference

https://typst.app/docs/reference/math/variants/
