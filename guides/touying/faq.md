# Frequently Asked Questions

> Source: <https://touying-typ.github.io/docs/faq>

A condensed reference to the most-asked questions about Touying. For
deeper explanations follow the cross-references into the tutorial pages.

## Themes and configuration

### How do I choose or switch themes?

```typst
#import "@preview/touying:0.7.3": *
#import themes.simple: *

#show: simple-theme

= Section
== Slide
This uses the simple theme.
```

Available themes: `simple`, `default`, `metropolis`, `aqua`, `dewdrop`,
`stargazer`, `university`. See [`themes/`](./themes/).

### How do I customize theme colors?

Pass `config-colors(...)`:

```typst
#show: simple-theme.with(
  aspect-ratio: "16-9",
  config-colors(primary: rgb("#d94f00")),
)
```

## Layout and columns

### Two-column layout?

```typst
#slide(composer: (1fr, 1fr))[
  == Left
][
  == Right
]
```

For unequal widths use `(2fr, 1fr)` etc.

### Absolute positioning?

```typst
#slide[
  Main slide content here.
  #place(bottom + right, dx: -1em, dy: -1em)[
    #rect(fill: blue.lighten(80%), inset: 0.5em)[Note]
  ]
]
```

### Fit content to the remaining slide height/width?

`utils.fit-to-height(1fr)[...]` or `utils.fit-to-width(1fr)[...]`. See
[`tutorial/utilities/01-fit-to.md`](./tutorial/utilities/01-fit-to.md).

## Table of contents

### Display a table of contents?

```typst
== Outline <touying:hidden>
#components.adaptive-columns(outline(title: none, indent: 1em))
```

### Add numbering to sections?

```typst
#import "@preview/numbly:0.1.0": numbly
#set heading(numbering: numbly("{1}.", default: "1.1"))
```

### Progressive (highlighted) outline?

`#components.progressive-outline()` — see
[`tutorial/progress/02-sections.md`](./tutorial/progress/02-sections.md).

## Bibliography and citations

### Citations as footnotes?

```typst
#show: simple-theme.with(
  config-common(show-bibliography-as-footnote: bibliography(bib)),
)
```

### Bibliography slide at the end?

```typst
== References
#magic.bibliography(title: none)
```

## Speaker notes

### Add speaker notes?

```typst
#slide[
  == My Slide
  Visible content.
  #speaker-note[
    - Remind the audience.
    - Time check at 10 min.
  ]
]
```

### Show speaker notes on a second screen?

```typst
#show: simple-theme.with(
  config-common(show-notes-on-second-screen: right),
)
```

Compatible with [pdfpc](./external/04-pdfpc.md) and
[pympress](./external/03-pympress.md).

## Slide numbering and appendix

### Display slide numbers in the footer?

```typst
#show: simple-theme.with(
  config-page(
    footer: context [
      #utils.slide-counter.display() / #utils.last-slide-number
    ],
  ),
)
```

### Mark a slide as unnumbered?

Add `<touying:unnumbered>` to the heading.

### Appendix that doesn't affect the slide count?

```typst
= Main
== A
== B
#show: appendix
= Appendix
== Backup
```

## Animations and dynamic content

### `#pause` to reveal step-by-step?

```typst
#slide[
  First.
  #pause
  Second.
  #pause
  Third.
]
```

### Show content only on specific subslides?

```typst
#slide[
  #only("1")[Subslide 1 only.]
  #only("2-")[From subslide 2 onward.]
  #uncover("3-")[Reveal at 3, space reserved before.]
]
```

### Why doesn't `#pause` work inside `context`?

`#pause` uses metadata injection that doesn't survive `context { ... }`.
Use callback-style:

```typst
#slide(self => {
  let (uncover, only) = utils.methods(self)
  [First content.]
  uncover("2-")[Revealed on subslide 2.]
  only("3")[Only on subslide 3.]
})
```

### `#pause` inside CeTZ?

```typst
#let cetz-canvas = touying-reducer.with(
  reduce: cetz.canvas,
  cover: cetz.draw.hide.with(bounds: true),
)
#slide[
  #cetz-canvas({
    import cetz.draw: *
    rect((0, 0), (4, 3))
    (pause,)
    circle((2, 1.5), radius: 1)
  })
]
```

### `#pause` inside Fletcher?

```typst
#let fletcher-diagram = touying-reducer.with(
  reduce: fletcher.diagram,
  cover: fletcher.hide,
)
#slide[
  #fletcher-diagram(
    node((0, 0), [A]),
    edge("->"),
    (pause,),
    node((1, 0), [B]),
  )
]
```

### Alternative content across subslides?

```typst
#slide[
  The answer is: #alternatives[42][*forty-two*][_the ultimate answer_].
]
```

### Handout mode (no animations)?

```typst
#show: simple-theme.with(config-common(handout: true))
```

Only the final subslide of each slide is output.

## Fonts and text

### Change the font?

```typst
#set text(font: "New Computer Modern", size: 22pt)
#show math.equation: set text(font: "New Computer Modern Math")
```

### Justify text?

```typst
#set par(justify: true)
```

## Headings and sections

### Disable automatic section slides?

```typst
#show: metropolis-theme.with(config-common(new-section-slide-fn: none))
```

### Write content for sections that have section slides?

Use `#pagebreak()` or `---` after `= Section`:

```typst
= Section
---
Here is my content for this section.
== Slide
And this works normally.
```

Or set `config-common(receive-body-for-new-section-slide-fn: false)`.

### Hide a slide from the output entirely?

`<touying:hidden>` on the heading.

### Exclude a slide from the outline?

`<touying:unoutlined>` on the heading.

### Control which heading level creates a new slide?

```typst
#show: simple-theme.with(config-common(slide-level: 2))
```

### Custom header / footer?

```typst
#show: default-theme.with(
  config-page(
    header: text(gray)[My Custom Header],
    footer: context align(right, text(gray)[
      Slide #utils.slide-counter.display()
    ]),
  ),
)
```

## `config-common` reference

### Prevent slide overflow?

```typst
#show: simple-theme.with(config-common(breakable: false))
// or with visual clipping:
#show: simple-theme.with(config-common(breakable: false, clip: true))
// or skipping the extra layout pass:
#show: simple-theme.with(config-common(breakable: false, detect-overflow: false))
```

### Semi-transparent cover instead of full hide?

```typst
#show: simple-theme.with(config-methods(cover: utils.semi-transparent-cover))
```

### Run code before every slide (`preamble`)?

```typst
#show: simple-theme.with(
  config-common(
    preamble: text(gray)[This appears before every slide],
    subslide-preamble: (2: [Special prelude for subslide 2]),
  ),
)
```

### `---` to separate slides?

```typst
#show: simple-theme.with(
  config-common(horizontal-line-to-pagebreak: true),  // (default)
)
```

## Testing and development

### Run Touying's test suite?

```sh
cargo binstall tytanic
tt run
```

Test layout: `tests/features/`, `tests/themes/`,
`tests/integration/`, `tests/issues/`, `tests/examples/`.

### Contribute?

1. Fork on GitHub.
2. Branch.
3. Follow existing style; format with [typstyle](https://github.com/Myriad-Dreamin/typstyle).
4. `tt run`.
5. PR with a clear description.

## Miscellaneous

### Set title / author / date / etc.?

```typst
#show: metropolis-theme.with(
  aspect-ratio: "16-9",
  config-info(
    title: [My Presentation],
    subtitle: [A Subtitle],
    author: [Jane Doe],
    date: datetime.today(),
    institution: [My University],
    contact: [contact\@mail.com],
  ),
)
#title-slide()
```

### Override config for a single slide?

```typst
#touying-set-config(config-page(fill: rgb("#fff3cd")))[
  #slide[This slide has a yellow background.]
]
```

### Access global / slide config?

```typst
#slide(config: config-colors(primary: rgb("ABCDEF")))[
  #touying-get-config().info.author
  #touying-get-config().colors.primary
]
```

### Compile?

```sh
typst compile slides.typ          # one-shot
typst watch   slides.typ          # live preview
```

Or use the [Tinymist](https://marketplace.visualstudio.com/items?itemName=myriad-dreamin.tinymist)
VS Code extension.

### Multi-file presentation?

```typst
// main.typ
#import "@preview/touying:0.7.3": *
#import themes.simple: *
#show: simple-theme.with(aspect-ratio: "16-9")

#include "intro.typ"
#include "methods.typ"
#include "results.typ"
```

See [`tutorial/06-multi-file.md`](./tutorial/06-multi-file.md).

### Display the current section in the header?

```typst
#show: default-theme.with(
  config-page(
    header: context text(gray)[
      #utils.display-current-heading(level: 1)
    ],
  ),
)
```

### Use Touying with `pinit`?

Just import both:

```typst
#import "@preview/touying:0.7.3": *
#import "@preview/pinit:0.2.2": *
```

For animated reveals interleaved with pinit, use callback-style.

### Freeze figure / equation counters across subslides?

```typst
#show: simple-theme.with(config-common(frozen-counters: true))
// or list specific counters:
#show: simple-theme.with(config-common(frozen-counters: (theorem-counter,)))
```

### Disable / enable warnings?

```typst
#touying-disable-warnings
#touying-enable-warnings
```

Or via `uniwarn`:

```typst
#import "@preview/uniwarn:0.1.0"
#uniwarn.disable-warnings("touying")
#uniwarn.enable-warnings("touying")
```
