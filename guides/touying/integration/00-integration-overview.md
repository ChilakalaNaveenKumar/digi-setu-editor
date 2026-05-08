# Package Integration — Overview

> Source: <https://touying-typ.github.io/docs/category/package-integration>

Touying plays nicely with the wider Typst ecosystem. The pages here cover
the most common integrations.

| File | Package | Why it matters |
| ---- | ------- | -------------- |
| [`01-pinit.md`](./01-pinit.md)       | [`pinit`](https://github.com/OrangeX4/typst-pinit/) | Absolute / pin-relative positioning — arrows, callouts, highlights. |
| [`02-mitex.md`](./02-mitex.md)       | [`mitex`](https://github.com/mitex-rs/mitex)        | Paste LaTeX equations directly without rewriting in Typst syntax. |
| [`03-cetz.md`](./03-cetz.md)         | [`cetz`](https://typst.app/universe/package/cetz)   | Wrap CeTZ canvases with `touying-reducer` for animated drawings. |
| [`04-fletcher.md`](./04-fletcher.md) | [`fletcher`](https://typst.app/universe/package/fletcher) | Wrap Fletcher diagrams with `touying-reducer` for animated diagrams. |
| [`05-codly.md`](./05-codly.md)       | [`codly`](https://github.com/Dherse/codly)          | Pretty code blocks with line numbers + animated reveal via `touying-raw`. |
| [`06-theorion.md`](./06-theorion.md) | [`theorion`](https://github.com/OrangeX4/typst-theorion) | Theorem / lemma / definition / proof environments. |

## Common pattern: `touying-reducer`

For drawing packages whose output is a single function (`cetz.canvas`,
`fletcher.diagram`), Touying wraps them in a **reducer** that interprets
animation primitives:

```typst
#let cetz-canvas = touying-reducer.with(
  reduce: cetz.canvas,
  cover: cetz.draw.hide.with(bounds: true),
)

#let fletcher-diagram = touying-reducer.with(
  reduce: fletcher.diagram,
  cover: fletcher.hide,
)
```

After binding, you can use `pause`, `meanwhile`, `only`, `uncover` inside
the canvas. See [`05-other.md`](../tutorial/dynamic/05-other.md) for the
mechanics.

## Common pattern: `preamble`

For packages that need per-page initialisation (`codly`, `pdfpc`), use
`config-common(preamble: { ... })`:

```typst
#show: simple-theme.with(
  config-common(preamble: {
    codly(languages: codly-languages)
  }),
)
```

## Common pattern: `frozen-counters`

For packages that maintain counters that should not advance per-subslide
(`theorion` and friends), freeze them:

```typst
config-common(frozen-counters: (theorem-counter,))
```
