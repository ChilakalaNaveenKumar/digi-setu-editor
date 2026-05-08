# 07 — Build Your Own Theme

> Source: <https://touying-typ.github.io/docs/tutorials/build-your-own-theme>

This page walks through creating a complete custom theme — the *Bamboo*
theme — from scratch. The pieces you typically need:

1. A `xxx-theme(...)` function (the show-rule entry point).
2. A color theme via `config-colors(...)`.
3. A custom header.
4. A custom footer.
5. A `slide` method.
6. Special slide methods: `title-slide`, `focus-slide`, `new-section-slide`.

## Modifying an existing theme (the easy path)

If you only want to tweak an existing theme:

1. Copy the file from `themes/` in
   [the Touying repo](https://github.com/touying-typ/touying/tree/main/themes)
   to your project, e.g. `themes/university.typ` → local `university.typ`.
2. Replace the import at the top — change
   `#import "../src/exports.typ": *` to `#import "@preview/touying:0.7.3": *`.

```typst
#import "@preview/touying:0.7.3": *
#import "university.typ": *
#show: university-theme.with(
  aspect-ratio: "16-9",
  config-info(
    title: [Title],
    author: [Authors],
    date: datetime.today(),
    institution: [Institution],
    logo: emoji.school,
  ),
)
```

You can now edit `university.typ` freely.

## Importing inside the theme

If the theme is for your own use only, import Touying directly:

```typst
#import "@preview/touying:0.7.3": *
```

If you want it to live inside the Touying repo's `themes/` directory,
change the import to:

```typst
#import "../src/exports.typ": *
```

…and add `#import "bamboo.typ"` to `themes/themes.typ`.

## `register` function and `init` method

The first job of a theme is to set the page aspect ratio and base font
size. Touying expects a `<theme>-theme` function that wraps everything in
`touying-slides.with(...)`:

```typst
// bamboo.typ
#import "@preview/touying:0.7.3": *

#let bamboo-theme(
  aspect-ratio: "16-9",
  ..args,
  body,
) = {
  set text(size: 20pt)
  show: touying-slides.with(
    config-page(paper: "presentation-" + aspect-ratio),
    config-common(slide-fn: slide),
    ..args,
  )
  body
}
```

```typst
// main.typ
#import "@preview/touying:0.7.3": *
#import "bamboo.typ": *

#show: bamboo-theme.with(aspect-ratio: "16-9")

= First Section
== First Slide
A slide with a title and an *important* information.
```

If you need access to `self`, register an `init` callback via
`config-methods(init: (self: none, body) => { ... })`.

## Color theme

Touying's color system has two dimensions:

- **Hue:** `neutral`, `primary`, `secondary`, `tertiary`.
- **Brightness:** `default`, `light`, `lighter`, `lightest`, `dark`,
  `darker`, `darkest`.

Set defaults via `config-colors(...)`:

```typst
config-colors(
  primary: rgb("#5E8B65"),       // Bamboo green
  neutral-lightest: rgb("#ffffff"),
  neutral-darkest: rgb("#000000"),
)
```

Read them later via `self.colors.primary`, etc.

Users can override at any time:

```typst
#show: touying-set-config.with(config-colors(
  primary: blue,
  neutral-lightest: rgb("#ffffff"),
  neutral-darkest: rgb("#000000"),
))
```

## Practical: custom `alert`

Add an `#alert[...]` function similar to `#strong[...]`:

```typst
config-methods(alert: (self: none, it) => text(fill: self.colors.primary, it))
```

Or use the shorthand:

```typst
config-methods(alert: utils.alert-with-primary-color)
```

## Custom header and footer

Save the per-slide title via `config-store(title: none)`, then build a
`header(self)` and `footer(self)` function:

```typst
let header(self) = {
  set align(top)
  show: components.cell.with(fill: self.colors.primary, inset: 1em)
  set align(horizon)
  set text(fill: self.colors.neutral-lightest, size: .7em)
  utils.display-current-heading(level: 1)
  linebreak()
  set text(size: 1.5em)
  if self.store.title != none {
    utils.call-or-display(self, self.store.title)
  } else {
    utils.display-current-heading(level: 2)
  }
}

let footer(self) = {
  set align(bottom)
  show: pad.with(.4em)
  set text(fill: self.colors.neutral-darkest, size: .8em)
  utils.call-or-display(self, self.store.footer)
  h(1fr)
  context utils.slide-counter.display() + " / " + utils.last-slide-number
}
```

Note the helpers:

- `components.cell` is `block.with(width: 100%, height: 100%, ...)`.
- `utils.call-or-display(self, value)` handles the case where `value` may
  be either content **or** a `(self) => content` function.
- `utils.display-current-heading(level: N)` queries the latest heading.

Then plug them into a custom `slide` function:

```typst
#let slide(title: auto, ..args) = touying-slide-wrapper(self => {
  if title != auto {
    self.store.title = title
  }
  // ... build header(self) and footer(self) as above ...
  self = utils.merge-dicts(
    self,
    config-page(header: header, footer: footer),
  )
  touying-slide(self: self, ..args)
})
```

Register it:

```typst
config-methods(slide: slide)
// also: config-page(margin: (top: 4em, bottom: 1.5em, x: 2em))
```

## Custom special slides

```typst
#let title-slide(..args) = touying-slide-wrapper(self => {
  let info = self.info + args.named()
  let body = {
    set align(center + horizon)
    block(
      fill: self.colors.primary,
      width: 80%,
      inset: (y: 1em),
      radius: 1em,
      text(size: 2em, fill: self.colors.neutral-lightest, weight: "bold", info.title),
    )
    set text(fill: self.colors.neutral-darkest)
    if info.author != none { block(info.author) }
    if info.date != none { block(utils.display-info-date(self)) }
    if info.contact != none { block(info.contact) }
  }
  touying-slide(self: self, body)
})

#let new-section-slide(self: none, body) = touying-slide-wrapper(self => {
  let main-body = {
    set align(center + horizon)
    set text(size: 2em, fill: self.colors.primary, weight: "bold", style: "italic")
    utils.display-current-heading(level: 1)
  }
  touying-slide(self: self, main-body)
})

#let focus-slide(body) = touying-slide-wrapper(self => {
  self = utils.merge-dicts(self, config-page(
    fill: self.colors.primary,
    margin: 2em,
  ))
  set text(fill: self.colors.neutral-lightest, size: 2em)
  touying-slide(self: self, align(horizon + center, body))
})
```

Register `new-section-slide` so it auto-fires on level-1 headings:

```typst
config-common(
  slide-fn: slide,
  new-section-slide-fn: new-section-slide,
)
```

## Example

See [`examples/07-build-your-own-theme/`](./examples/07-build-your-own-theme/)
for the runnable Bamboo theme as `bamboo.typ` plus the `main.typ` driver.

## Pitfalls

- The `slide(title: auto, ..args)` pattern is canonical — `title: auto`
  means "use the heading-derived value", `title: none` means "no title
  this slide", and `title: <content>` means "override".
- `touying-slide-wrapper(self => { ... })` is mandatory — it gives you
  the up-to-date `self` (with all overrides applied).
- `utils.merge-dicts(self, config-page(...))` is the canonical way to
  override `self.page` from inside a slide function.
