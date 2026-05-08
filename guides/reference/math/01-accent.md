# `math.accent(base, accent, size: 100% + 0pt, dotless: true)` — attach an accent to a base

Adds a diacritical mark (hat, tilde, dot, arrow, ...) above a base expression. The base can be a single letter or several letters; the accent is auto-stretched to fit.

## Parameters

| Param      | Type                       | Default        | Notes                                                                                |
| ---------- | -------------------------- | -------------- | ------------------------------------------------------------------------------------ |
| `base`     | content                    | required       | Letter / expression to accent.                                                       |
| `accent`   | str / content (symbol)     | required       | The accent. Pass a math-mode symbol (`arrow`, `tilde`, `hat`, `dot`, ...) or a literal char. |
| `size`     | relative                   | `100% + 0pt`   | Width of the accent relative to the base.                                            |
| `dotless`  | bool                       | `true`         | When ON, removes the dot of `i`/`j` under top accents (OpenType `dtls` feature).     |

## Built-in shortcut functions

Each of these is a thin wrapper around `accent(base, <symbol>)`:

| Accent           | Function                | Glyph |
| ---------------- | ----------------------- | ----- |
| Grave            | `grave(x)`               | `̀`   |
| Acute            | `acute(x)`               | `´`   |
| Circumflex       | `hat(x)`                 | `^`   |
| Tilde            | `tilde(x)`               | `~`   |
| Macron           | `macron(x)`              | `¯`   |
| Dash             | `dash(x)`                | `‾`   |
| Breve            | `breve(x)`               | `˘`   |
| Dot              | `dot(x)`                 | `.`   |
| Diaeresis        | `dot.double(x)` / `diaer(x)` | `¨` |
| Triple dot       | `dot.triple(x)`          | `⃛`   |
| Quadruple dot    | `dot.quad(x)`            | `⃜`   |
| Circle           | `circle(x)`              | `∘`   |
| Double acute     | `acute.double(x)`        | `˝`   |
| Caron            | `caron(x)`               | `ˇ`   |
| Right arrow      | `arrow(x)` / `->`         | `→`   |
| Left arrow       | `arrow.l(x)` / `<-`       | `←`   |
| Left/right arrow | `arrow.l.r(x)`            | `↔`   |
| Right harpoon    | `harpoon(x)`              | `⇀`   |
| Left harpoon     | `harpoon.lt(x)`           | `↼`   |

## Examples (compile-verified)

- `examples/01-accent/01-accent.typ` — built-in shortcuts, multi-letter base, `size`, `dotless` toggle.

## Reference

https://typst.app/docs/reference/math/accent/
