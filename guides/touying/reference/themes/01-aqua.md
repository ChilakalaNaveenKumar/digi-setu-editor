# Reference — `aqua` Theme

> Source: [themes/aqua.typ](https://github.com/touying-typ/touying/blob/main/themes/aqua.typ)
>
> Tutorial-level usage: [`../../themes/05-aqua.md`](../../themes/05-aqua.md).

```typst
#import "@preview/touying:0.7.3": *
#import themes.aqua: *
```

Exported symbols:

| Name | Kind | Notes |
| ---- | ---- | ----- |
| `aqua-theme` | show-rule fn | The entry point. |
| `slide` | slide fn | Default slide. |
| `title-slide` | slide fn | Reads from `self.info`. |
| `outline-slide` | slide fn | Renders an outline. `enum-args:`, `leading:`. |
| `focus-slide` | slide fn | Background = `self.colors.primary`. |
| `new-section-slide` | slide fn | Manually call to start a new section. |
| `alert` | content fn | Use with `#show strong: alert`. |

## `aqua-theme.with(..)` parameters

| Name | Default | Notes |
| ---- | ------- | ----- |
| `aspect-ratio` | `"16-9"` | `"16-9"` or `"4-3"`. |
| `header` | `utils.display-current-heading()` | Or a `(self) =>` callback. |
| `footer` | `context utils.slide-counter.display()` | Or a callback. |

Aqua does **not** install an automatic `new-section-slide-fn` — call
`new-section-slide(title)` manually when you want a section title page.

## Default colors

```typst
config-colors(
  primary:           rgb("#003F88"),
  primary-light:     rgb("#2159A5"),
  primary-lightest:  rgb("#F2F4F8"),
  neutral-lightest:  rgb("#FFFFFF"),
)
```

## See also

- [`../../themes/05-aqua.md`](../../themes/05-aqua.md) — full tutorial.
- [`../core/04-slides.md`](../core/04-slides.md) — `slide(...)`
  parameter contract.
