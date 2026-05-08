# Themes — Overview

> Source: <https://touying-typ.github.io/docs/category/themes>

Touying ships seven built-in themes (six concrete, plus the *custom*
recipe). Each theme exports its own `<name>-theme(..)` show-rule
function plus a slide function family — typically `slide`, `title-slide`,
`focus-slide`, and a couple of theme-specific extras.

| File | Theme | One-line description |
| ---- | ----- | -------------------- |
| [`01-simple.md`](./01-simple.md)         | `simple`     | Polylux-derived, minimal, by Andreas Kröpelin. |
| [`02-metropolis.md`](./02-metropolis.md) | `metropolis` | Modern, Fira Sans + Fira Math, port of the Beamer theme. |
| [`03-dewdrop.md`](./03-dewdrop.md)       | `dewdrop`    | Mini-slides / sidebar navigation, by OrangeX4. |
| [`04-university.md`](./04-university.md) | `university` | Three-column footer, top progress bar, by Pol Dellaiera. |
| [`05-aqua.md`](./05-aqua.md)             | `aqua`       | Beautiful blue gradient backgrounds, by @pride7. |
| [`06-stargazer.md`](./06-stargazer.md)   | `stargazer`  | Versatile, BUAA-derived, four-column footer, by Coekjan. |
| [`07-custom.md`](./07-custom.md)         | *(custom)*   | How to copy / extend an existing theme, or build one from scratch. |

## Common shape

All built-in themes share the same import-and-show idiom:

```typst
#import "@preview/touying:0.7.3": *
#import themes.<name>: *

#show: <name>-theme.with(
  aspect-ratio: "16-9",   // or "4-3"
  config-info(
    title:       [...],
    subtitle:    [...],
    author:      [...],
    date:        datetime.today(),
    institution: [...],
  ),
)

#title-slide()
== First Slide
Hello.
```

## Picking a theme

| Need | Recommended |
| ---- | ----------- |
| Bare minimum, custom everything | `simple` |
| Modern, talks at conferences | `metropolis` |
| Big lecture deck with TOC | `dewdrop` (mini-slides nav) |
| University course / thesis defence | `university` or `stargazer` |
| Visually distinctive, blue gradient | `aqua` |
| Fully bespoke | follow [`07-custom.md`](./07-custom.md) and the [Build Your Own Theme](../tutorial/07-build-your-own-theme.md) tutorial |

## Browse more

- Built-in showcase: <https://touying-typ.github.io/themes/>
- Community themes on Typst Universe: <https://typst.app/universe/search/?q=touying>
- Community gallery: <https://github.com/touying-typ/touying/wiki>
