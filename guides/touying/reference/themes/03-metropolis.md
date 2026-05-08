# Reference — `metropolis` Theme

> Source: [themes/metropolis.typ](https://github.com/touying-typ/touying/blob/main/themes/metropolis.typ)
>
> Tutorial-level usage: [`../../themes/02-metropolis.md`](../../themes/02-metropolis.md).

```typst
#import "@preview/touying:0.7.3": *
#import themes.metropolis: *
```

Exported:

| Name | Kind |
| ---- | ---- |
| `metropolis-theme` | show-rule fn |
| `slide` | slide fn (with `title:`, `footer:`, `align:` params) |
| `title-slide` | slide fn |
| `outline-slide` *(v0.7.3+)* | slide fn |
| `focus-slide` | slide fn |
| `new-section-slide` | slide fn |

## `metropolis-theme.with(..)` parameters

| Name | Default | Notes |
| ---- | ------- | ----- |
| `aspect-ratio` | `"16-9"` | |
| `align` | `horizon` | Vertical alignment. |
| `header` | `utils.display-current-heading(setting: utils.fit-to-width.with(grow: false, 100%))` | |
| `header-right` | `self => self.info.logo` | |
| `footer` | `[]` | |
| `footer-right` | `context utils.slide-counter.display() + " / " + utils.last-slide-number` | |
| `footer-progress` | `true` | Bottom progress bar. |

## Default colors

```typst
config-colors(
  primary:           rgb("#eb811b"),
  primary-light:     rgb("#d6c6b7"),
  secondary:         rgb("#23373b"),
  neutral-lightest:  rgb("#fafafa"),
  neutral-dark:      rgb("#23373b"),
  neutral-darkest:   rgb("#23373b"),
)
```

## Recommended fonts

Fira Sans + Fira Math:

```typst
#set text(font: "Fira Sans", weight: "light", size: 20pt)
#show math.equation: set text(font: "Fira Math")
```

## See also

- [`../../themes/02-metropolis.md`](../../themes/02-metropolis.md) — tutorial.
- [`../../tutorial/03-sections.md`](../../tutorial/03-sections.md) — sections / `slide-level`.
