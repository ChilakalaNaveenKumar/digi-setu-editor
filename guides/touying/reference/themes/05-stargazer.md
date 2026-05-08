# Reference — `stargazer` Theme

> Source: [themes/stargazer.typ](https://github.com/touying-typ/touying/blob/main/themes/stargazer.typ)
>
> Tutorial-level usage: [`../../themes/06-stargazer.md`](../../themes/06-stargazer.md).

```typst
#import "@preview/touying:0.7.3": *
#import themes.stargazer: *
```

Exported:

| Name | Kind |
| ---- | ---- |
| `stargazer-theme` | show-rule fn |
| `slide` | slide fn (`title:`, `footer:`, `align:`) |
| `title-slide` | slide fn (`extra:`) |
| `outline-slide` | TOC slide |
| `focus-slide` | bg = `self.colors.primary-dark` |
| `new-section-slide` | manual `(short-title: auto, title)` |
| `tblock` | theorem-style highlight block (`title:`) |

## `stargazer-theme.with(..)` parameters

| Name | Default | Notes |
| ---- | ------- | ----- |
| `aspect-ratio` | `"16-9"` | |
| `align` | `horizon` | |
| `alpha` | `20%` | Background transparency. |
| `title` | `utils.display-current-heading()` | Header content. |
| `progress-bar` | `true` | Bottom progress bar. |
| `footer-columns` | `(25%, 25%, 1fr, 5em)` | |
| `footer-a` | `self => self.info.author` | |
| `footer-b` | `self => utils.display-info-date(self)` | |
| `footer-c` | `self => if self.info.short-title == auto { self.info.title } else { self.info.short-title }` | |
| `footer-d` | `context utils.slide-counter.display() + " / " + utils.last-slide-number` | |

## Default colors

```typst
config-colors(
  primary:           rgb("#005bac"),
  primary-dark:      rgb("#004078"),
  secondary:         rgb("#ffffff"),
  tertiary:          rgb("#005bac"),
  neutral-lightest:  rgb("#ffffff"),
  neutral-darkest:   rgb("#000000"),
)
```

## `tblock(title: ..., body)`

Stargazer-only theorem block:

```typst
#tblock(title: [Theorem])[
  A simple theorem.
  $ x_(n+1) = (x_n + a / x_n) / 2 $
]
```

For cross-theme theorem environments, see [Theorion integration](../../integration/06-theorion.md).

## See also

- [`../../themes/06-stargazer.md`](../../themes/06-stargazer.md) — tutorial.
