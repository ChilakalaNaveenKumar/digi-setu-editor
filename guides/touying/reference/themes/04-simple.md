# Reference — `simple` Theme

> Source: [themes/simple.typ](https://github.com/touying-typ/touying/blob/main/themes/simple.typ)
>
> Tutorial-level usage: [`../../themes/01-simple.md`](../../themes/01-simple.md).

```typst
#import "@preview/touying:0.7.3": *
#import themes.simple: *
```

Exported:

| Name | Kind |
| ---- | ---- |
| `simple-theme` | show-rule fn |
| `slide` | default slide |
| `centered-slide` | content centered, optional `section:` arg |
| `title-slide` | alias for `centered-slide` (Polylux compat) |
| `focus-slide` | full-bleed primary-color slide; `foreground:`, `background:` |

## `simple-theme.with(..)` parameters

| Name | Default | Notes |
| ---- | ------- | ----- |
| `aspect-ratio` | `"16-9"` | |
| `header` | `utils.display-current-heading(setting: utils.fit-to-width.with(grow: false, 100%))` | |
| `header-right` | `self => self.info.logo` | |
| `footer` | `[]` | |
| `footer-right` | `context utils.slide-counter.display() + " / " + utils.last-slide-number` | |
| `primary` | `aqua.darken(50%)` | |
| `subslide-preamble` | adds the subsection title to the slide | |

`simple-theme` registers `config-common(slide-fn: slide,
new-section-slide-fn: new-section-slide)` so level-1 headings auto-fire
a section slide. Suppress with `config-common(new-section-slide-fn:
none)`.

## See also

- [`../../themes/01-simple.md`](../../themes/01-simple.md) — tutorial.
- [`../../tutorial/02-code-styles.md`](../../tutorial/02-code-styles.md)
  — convention-over-configuration discussion.
