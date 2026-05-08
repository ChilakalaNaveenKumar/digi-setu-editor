# Reference — `dewdrop` Theme

> Source: [themes/dewdrop.typ](https://github.com/touying-typ/touying/blob/main/themes/dewdrop.typ)
>
> Tutorial-level usage: [`../../themes/03-dewdrop.md`](../../themes/03-dewdrop.md).

```typst
#import "@preview/touying:0.7.3": *
#import themes.dewdrop: *
```

Exported:

| Name | Kind | Notes |
| ---- | ---- | ----- |
| `dewdrop-theme` | show-rule fn | The entry point. |
| `slide` | slide fn | Default slide with mini-slides nav + footer. |
| `title-slide` | slide fn | Reads from `self.info`. `extra:`. |
| `outline-slide` | slide fn | Outline with mini-slides nav. |
| `focus-slide` | slide fn | Background = `self.colors.primary`. |
| `alert` | content fn | Combine with `#show strong: alert`. |

## `dewdrop-theme.with(..)` parameters

| Name | Default | Notes |
| ---- | ------- | ----- |
| `aspect-ratio` | `"16-9"` | `"16-9"` / `"4-3"`. |
| `navigation` | `"mini-slides"` | `"mini-slides"` or `"sidebar"`. |
| `mini-slides` | `(height: 4em, x: 2em, display-section: false, display-subsection: true, short-heading: true)` | Sub-dict for mini-slides config. |
| `alpha` | `70%` | Transparency of inactive nav entries. |
| `footer` | `[]` | Footer content / callback. |

Sub-keys of `mini-slides`:

- `height` *(default `2em`)* — bar height.
- `x` *(default `2em`)* — x padding.
- `section` *(default `false`)* — show inter-section slides.
- `subsection` *(default `true`)* — split per subsection (squashed if `false`).

## Default colors

```typst
config-colors(
  neutral-darkest:  rgb("#000000"),
  neutral-dark:     rgb("#202020"),
  neutral-light:    rgb("#f3f3f3"),
  neutral-lightest: rgb("#ffffff"),
  primary:          primary,  // user-supplied at register time
)
```

## Default `slide-level`

`3` — `=`/`==`/`===` map to section/subsection/subsubsection. Override
with `config-common(slide-level: 2)` for the typical
section/slide-title mapping.

## See also

- [`../../themes/03-dewdrop.md`](../../themes/03-dewdrop.md) — full tutorial.
- [`../core/03-components.md`](../core/03-components.md) — `mini-slides`,
  `progressive-outline`.
