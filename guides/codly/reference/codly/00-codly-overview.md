# `codly(...)` — Overview

The single configuration entry point. `codly(...)` accepts **53 named
arguments**; this overview groups them by theme and links to the per-argument
page.

| File | Purpose | Page |
| ---- | ------- | ---- |
| [`01-codly.md`](./01-codly.md) | The full `codly(...)` signature, the set-rule semantics warning, and one-line summaries of every argument. | [`01-codly.md`](./01-codly.md) |

## All 53 arguments at a glance

### Activation

| Arg | Type | Default | Page |
| --- | ---- | ------- | ---- |
| `enabled` | bool | `true` | [`02-enabled.md`](./02-enabled.md) |

### Header / footer

| Arg | Type | Default | Page |
| --- | ---- | ------- | ---- |
| `header` | content / none | `none` | [`03-header.md`](./03-header.md) |
| `header-repeat` | bool | `false` | [`04-header-repeat.md`](./04-header-repeat.md) |
| `header-cell-args` | array / dict / args | `()` | [`05-header-cell-args.md`](./05-header-cell-args.md) |
| `header-transform` | function | `(x) => x` | [`06-header-transform.md`](./06-header-transform.md) |
| `footer` | content / none | `none` | [`07-footer.md`](./07-footer.md) |
| `footer-repeat` | bool | `false` | [`08-footer-repeat.md`](./08-footer-repeat.md) |
| `footer-cell-args` | array / dict / args | `()` | [`09-footer-cell-args.md`](./09-footer-cell-args.md) |
| `footer-transform` | function | `(x) => x` | [`10-footer-transform.md`](./10-footer-transform.md) |

### Line-number ranges & offsets

| Arg | Type | Default | Page |
| --- | ---- | ------- | ---- |
| `offset` | int | `0` | [`11-offset.md`](./11-offset.md) |
| `offset-from` | none / label | `none` | [`12-offset-from.md`](./12-offset-from.md) |
| `range` | none / array | `none` | [`13-range.md`](./13-range.md) |
| `ranges` | none / array | `none` | [`14-ranges.md`](./14-ranges.md) |
| `smart-skip` | bool / dict | `false` | [`15-smart-skip.md`](./15-smart-skip.md) |

### Languages

| Arg | Type | Default | Page |
| --- | ---- | ------- | ---- |
| `languages` | dict | `(:)` | [`16-languages.md`](./16-languages.md) |
| `default-color` | color / gradient / tiling | `rgb("#283593")` | [`17-default-color.md`](./17-default-color.md) |
| `aliases` | dict | `(:)` | [`54-aliases.md`](./54-aliases.md) |

### Block styling

| Arg | Type | Default | Page |
| --- | ---- | ------- | ---- |
| `radius` | length | `0.32em` | [`18-radius.md`](./18-radius.md) |
| `inset` | length / dict | `0.32em` | [`19-inset.md`](./19-inset.md) |
| `fill` | none / color / gradient / tiling | `none` | [`20-fill.md`](./20-fill.md) |
| `zebra-fill` | none / color / gradient / tiling | `luma(240)` | [`21-zebra-fill.md`](./21-zebra-fill.md) |
| `stroke` | none / stroke | `1pt + luma(240)` | [`22-stroke.md`](./22-stroke.md) |
| `breakable` | bool | `true` | [`36-breakable.md`](./36-breakable.md) |

### Language-pill styling

| Arg | Type | Default | Page |
| --- | ---- | ------- | ---- |
| `lang-inset` | length / dict | `0.32em` | [`23-lang-inset.md`](./23-lang-inset.md) |
| `lang-outset` | dict | `(x: 0.32em, y: 0em)` | [`24-lang-outset.md`](./24-lang-outset.md) |
| `lang-radius` | length | `0.32em` | [`25-lang-radius.md`](./25-lang-radius.md) |
| `lang-stroke` | none / stroke / function | `(lang) => lang.color + 0.5pt` | [`26-lang-stroke.md`](./26-lang-stroke.md) |
| `lang-fill` | none / color / gradient / tiling / function | `(lang) => lang.color.lighten(80%)` | [`27-lang-fill.md`](./27-lang-fill.md) |
| `lang-format` | type(auto) / none / function | `auto` | [`28-lang-format.md`](./28-lang-format.md) |
| `display-name` | bool | `true` | [`29-display-name.md`](./29-display-name.md) |
| `display-icon` | bool | `true` | [`30-display-icon.md`](./30-display-icon.md) |

### Line numbers

| Arg | Type | Default | Page |
| --- | ---- | ------- | ---- |
| `number-format` | function / none | `numbering.with("1")` | [`31-number-format.md`](./31-number-format.md) |
| `number-align` | alignment | `left + horizon` | [`32-number-align.md`](./32-number-align.md) |
| `number-placement` | str | `"inside"` | [`33-number-placement.md`](./33-number-placement.md) |
| `smart-indent` | bool | `true` | [`34-smart-indent.md`](./34-smart-indent.md) |
| `skip-last-empty` | bool | `true` | [`35-skip-last-empty.md`](./35-skip-last-empty.md) |

### Skips

| Arg | Type | Default | Page |
| --- | ---- | ------- | ---- |
| `skips` | array / none | `none` | [`37-skips.md`](./37-skips.md) |
| `skip-line` | content / none | `align(center)[ ... ]` | [`38-skip-line.md`](./38-skip-line.md) |
| `skip-number` | content / none | `[ ... ]` | [`39-skip-number.md`](./39-skip-number.md) |

### Annotations

| Arg | Type | Default | Page |
| --- | ---- | ------- | ---- |
| `annotations` | array / none | `none` | [`40-annotations.md`](./40-annotations.md) |
| `annotation-format` | none / function | `numbering.with("(1)")` | [`41-annotation-format.md`](./41-annotation-format.md) |

### Highlights

| Arg | Type | Default | Page |
| --- | ---- | ------- | ---- |
| `highlighted-lines` | array / none | `()` | [`42-highlighted-lines.md`](./42-highlighted-lines.md) |
| `highlighted-default-color` | color / tiling / gradient | `orange.lighten(60%)` | [`43-highlighted-default-color.md`](./43-highlighted-default-color.md) |
| `highlights` | array / none | `none` | [`44-highlights.md`](./44-highlights.md) |
| `highlight-radius` | length | `0.32em` | [`45-highlight-radius.md`](./45-highlight-radius.md) |
| `highlight-fill` | function | `(color) => color.lighten(80%)` | [`46-highlight-fill.md`](./46-highlight-fill.md) |
| `highlight-stroke` | stroke / function | `(color) => 0.5pt + color` | [`47-highlight-stroke.md`](./47-highlight-stroke.md) |
| `highlight-inset` | length / dict | `0.32em` | [`48-highlight-inset.md`](./48-highlight-inset.md) |
| `highlight-outset` | length / dict | `0em` | [`49-highlight-outset.md`](./49-highlight-outset.md) |
| `highlight-clip` | bool | `true` | [`50-highlight-clip.md`](./50-highlight-clip.md) |

### References

| Arg | Type | Default | Page |
| --- | ---- | ------- | ---- |
| `reference-by` | str | `"line"` | [`51-reference-by.md`](./51-reference-by.md) |
| `reference-sep` | str / content | `"-"` | [`52-reference-sep.md`](./52-reference-sep.md) |
| `reference-number-format` | function | `numbering.with("1")` | [`53-reference-number-format.md`](./53-reference-number-format.md) |

## Reading order

For first-time use, read [`01-codly.md`](./01-codly.md) for the full
function signature, then jump to whichever theme you actually need.
Helper functions that wrap a single `codly(...)` argument
(`codly-skip`, `codly-range`, `codly-offset`) live under
[`../functions/`](../functions/00-functions-overview.md).
