# `color` — Colors and Color Spaces

`color` is Typst's color value type. You construct colors via space-specific
factories (`rgb`, `cmyk`, `luma`, `oklab`, `oklch`, `color.linear-rgb`,
`color.hsl`, `color.hsv`) or by name from the predefined palette.

## Color spaces at a glance

| Space          | Constructor              | Notes                                                       |
| -------------- | ------------------------ | ----------------------------------------------------------- |
| sRGB           | `rgb(r, g, b, a)` or `rgb("#hex")` | The web/screen default. Components: `int 0..255` or `ratio`. |
| Grayscale (D65)| `luma(l, a)`             | Single lightness component.                                 |
| Device CMYK    | `cmyk(c, m, y, k)`       | For print targeting. Not allowed in PDF/A.                  |
| Oklab          | `oklab(l, a, b, alpha)`  | Perceptually uniform, best for **mixing/gradients**.        |
| Oklch          | `oklch(l, c, h, alpha)`  | Polar Oklab; great for **hue rotation**.                    |
| Linear RGB     | `color.linear-rgb(...)`  | sRGB without gamma — useful for blending.                   |
| HSL            | `color.hsl(h, s, l, a)`  | Manipulate by hue/saturation/lightness.                     |
| HSV            | `color.hsv(h, s, v, a)`  | Hue/saturation/value.                                       |

Choose **Oklab/Oklch** for any computation involving humans (mixing,
gradients, lightness ramps). Choose **rgb/cmyk** for hard-coded literals
matching brand colors or print specs.

## Predefined named colors

The following globals are always in scope (also accessible as `color.red` etc.):

| Name      | Definition                |
| --------- | ------------------------- |
| `black`   | `luma(0)`                 |
| `gray`    | `luma(170)`               |
| `silver`  | `luma(221)`               |
| `white`   | `luma(255)`               |
| `navy`    | `rgb("#001f3f")`          |
| `blue`    | `rgb("#0074d9")`          |
| `aqua`    | `rgb("#7fdbff")`          |
| `teal`    | `rgb("#39cccc")`          |
| `eastern` | `rgb("#239dad")`          |
| `purple`  | `rgb("#b10dc9")`          |
| `fuchsia` | `rgb("#f012be")`          |
| `maroon`  | `rgb("#85144b")`          |
| `red`     | `rgb("#ff4136")`          |
| `orange`  | `rgb("#ff851b")`          |
| `yellow`  | `rgb("#ffdc00")`          |
| `olive`   | `rgb("#3d9970")`          |
| `green`   | `rgb("#2ecc40")`          |
| `lime`    | `rgb("#01ff70")`          |

## Predefined color maps (for gradients)

Available under `color.map`:

`turbo`, `cividis`, `rainbow`, `spectral`, `viridis`, `inferno`, `magma`,
`plasma`, `rocket`, `mako`, `vlag`, `icefire`, `flare`, `crest`.

Spread one into a gradient:

```typst
#rect(fill: gradient.linear(..color.map.viridis), width: 100%, height: 14pt)
```

`rainbow` is decorative only — it isn't perceptually uniform and is hard to
read for color-blind audiences. Prefer `viridis`, `cividis`, or `crest`
for data visualization.

## Manipulating colors

| Method                            | What it does                                                          |
| --------------------------------- | --------------------------------------------------------------------- |
| `c.lighten(ratio)` / `c.darken(ratio)` | Move toward white / black by a percentage.                       |
| `c.saturate(ratio)` / `c.desaturate(ratio)` | Push saturation up / down.                                  |
| `c.negate(space: oklab)`          | Complementary color in the chosen space.                              |
| `c.rotate(angle, space: oklch)`   | Rotate hue.                                                           |
| `c.mix((other, weight), ..., space: oklab)` | Blend two or more colors with weights.                      |
| `c.transparentize(ratio)` / `c.opacify(ratio)` | Adjust alpha relative to the current alpha.                |
| `c.to-hex()`                      | `"#rrggbbaa"` (alpha omitted when 100%).                              |
| `c.components(alpha: true)`       | Array of components in this color's space.                            |
| `c.space()`                       | The constructor function (`rgb`, `oklab`, ...) for this color.        |

## Tips

- For consistent perceptual mixing leave the default `space: oklab`.
- For hue-only manipulation (a single rainbow stripe, hue rotation), use
  `oklch` or `hsl`.
- `rgb("#abc")` expands to `#aabbcc`. Three, four, six, or eight hex digits
  are accepted, optional leading `#`.
