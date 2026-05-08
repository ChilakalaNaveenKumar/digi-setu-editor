# `underline` — line below text

`underline(body: content, stroke: auto | stroke = auto, offset: auto | length = auto, extent: length = 0pt, evade: bool = true, background: bool = false) -> content`

Draws a horizontal line **below** the baseline.

```typst
This is #underline[important].
```

## Parameters (shared shape with `overline` and `strike`)

| Field        | Default  | What it does                                                          |
| ------------ | -------- | --------------------------------------------------------------------- |
| `stroke`     | `auto`   | `auto` = font color + font-recommended thickness                       |
| `offset`     | `auto`   | Distance below baseline; `auto` reads font tables                       |
| `extent`     | `0pt`    | Extra horizontal extent on each side; negative trims inward             |
| `evade`      | `true`   | Skip glyphs that would intersect the line (e.g. descenders `p q y g j`) |
| `background` | `false`  | `true` = behind glyphs; `false` = in front                              |

## Common patterns

### Underline all hyperlinks

The `link` element doesn't underline by default — many docs use:

```typst
#show link: underline
```

### Solid-bar emphasis (no glyph evasion)

For dramatic effect, set `evade: false` so the line goes through descenders:

```typst
#underline(evade: false)[heavy emphasis]
```

### Highlighter-like effect

Combine a thick translucent stroke with `background: true`:

```typst
#set underline(stroke: (thickness: 0.8em, paint: rgb("#ff04")))
#underline(background: true)[looks like a highlighter]
```

(Or just use `highlight` for the real thing.)

## Pitfalls

- **Default offset is font-dependent.** Don't hard-code `offset: 1pt` and expect consistency across fonts — leave `auto` unless you have a specific design.
- **`evade: true` can leave gaps you didn't expect** under descenders. If you want a continuous bar, switch to `evade: false`.
- **`extent` is per-side**, so `extent: 4pt` adds 4pt on the left AND 4pt on the right — net 8pt wider.
- **Wrapping to a new line restarts the underline.** A multi-line underlined block has independent underlines per visual line.
- **`underline` ≠ link semantically.** `#underline[text]` doesn't make the text clickable. Use `#link(dest)[text]` and a show rule for the visual style.
- **Setting `stroke: 0.5pt` (no color) takes auto color** — same shape as `overline`. Add `+ color` if you want both.

## Examples (compile-verified)

- `examples/13-underline/01-underline.typ` — defaults, custom stroke + offset, `extent`, `evade` on/off, `background: true` for a highlighter-style line, `#show link: underline` pattern.

## Reference

- Official: https://typst.app/docs/reference/text/underline/
- `overline`: https://typst.app/docs/reference/text/overline/
- `strike`: https://typst.app/docs/reference/text/strike/
- `link`: https://typst.app/docs/reference/model/link/
- `highlight`: https://typst.app/docs/reference/text/highlight/
