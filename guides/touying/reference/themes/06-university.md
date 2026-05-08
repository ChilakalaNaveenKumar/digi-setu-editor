# Reference — `university` Theme

> Source: [themes/university.typ](https://github.com/touying-typ/touying/blob/main/themes/university.typ)
>
> Tutorial-level usage: [`../../themes/04-university.md`](../../themes/04-university.md).

```typst
#import "@preview/touying:0.7.3": *
#import themes.university: *
```

Exported:

| Name | Kind |
| ---- | ---- |
| `university-theme` | show-rule fn |
| `slide` | slide fn (`title:`) |
| `title-slide` | slide fn (`logo:`, `authors:` *(array)*) |
| `focus-slide` | slide fn (`background-img:`, `background-color:`) |
| `matrix-slide` | slide fn (`columns:`, `rows:` — Polylux-style) |

## `university-theme.with(..)` parameters

| Name | Default | Notes |
| ---- | ------- | ----- |
| `aspect-ratio` | `"16-9"` | |
| `progress-bar` | `true` | Top progress bar. |
| `header` | `utils.display-current-heading(level: 2)` | |
| `header-right` | `self => self.info.logo` | |
| `footer-columns` | `(25%, 1fr, 25%)` | |
| `footer-a` | `self => self.info.author` | |
| `footer-b` | `self => if self.info.short-title == auto { self.info.title } else { self.info.short-title }` | |
| `footer-c` | (multi-element default — see below) | |

`footer-c` default:

```typst
self => {
  h(1fr)
  utils.display-info-date(self)
  h(1fr)
  context utils.slide-counter.display() + " / " + utils.last-slide-number
  h(1fr)
}
```

## Default colors

```typst
config-colors(
  primary:          rgb("#04364A"),
  secondary:        rgb("#176B87"),
  tertiary:         rgb("#448C95"),
  neutral-lightest: rgb("#ffffff"),
  neutral-darkest:  rgb("#000000"),
)
```

## `title-slide(logo: ..., authors: ..., ..args)`

`authors:` accepts an **array** even for a single author:
`authors: ([Solo Author],)`. This is what makes the multi-author layout
render correctly.

## `matrix-slide(columns: .., rows: ..)[..][..]`

Grid-style slide. Mirrors the Polylux University theme's
[matrix-slide](https://polylux.dev/book/themes/gallery/university.html).

```typst
#matrix-slide[ left ][ middle ][ right ]
#matrix-slide(columns: 1)[ top ][ bottom ]
#matrix-slide(columns: (1fr, 2fr, 1fr), ..(lorem(8),) * 9)
```

## See also

- [`../../themes/04-university.md`](../../themes/04-university.md) — tutorial.
- [`../../tutorial/03-sections.md`](../../tutorial/03-sections.md) —
  level-1 = section, level-2 = slide title.
