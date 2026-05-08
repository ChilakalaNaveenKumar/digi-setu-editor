# `aqua-theme` — Aqua Theme

> Source: <https://touying-typ.github.io/docs/themes/aqua>
>
> Created by [@pride7](https://github.com/pride7).

Beautiful blue gradient backgrounds drawn entirely with Typst's
visualization primitives.

## Initialization

```typst
#import "@preview/touying:0.7.3": *
#import themes.aqua: *

#show: aqua-theme.with(
  aspect-ratio: "16-9",
  config-info(
    title: [Title], subtitle: [Subtitle],
    author: [Authors], date: datetime.today(),
    institution: [Institution],
  ),
)
#title-slide()
#outline-slide()
```

## Parameters

`aqua-theme.with(..)` accepts:

- **`aspect-ratio`** *(default `"16-9"`)*.
- **`header`** *(default `utils.display-current-heading()`)*.
- **`footer`** *(default `context utils.slide-counter.display()`)*.

Aqua also exports `#alert[..]` — combine with `#show strong: alert`.

## Color theme

```typst
config-colors(
  primary:           rgb("#003F88"),
  primary-light:     rgb("#2159A5"),
  primary-lightest:  rgb("#F2F4F8"),
  neutral-lightest:  rgb("#FFFFFF"),
)
```

## Slide function family

```typst
#title-slide(..args)
#outline-slide(self: none, enum-args: (:), leading: 50pt)
#slide(repeat: auto, setting: body => body, composer: cols, title: auto)[ ... ]
#focus-slide[ ... ]
#new-section-slide(title)
```

`focus-slide` background = `self.colors.primary`.
`new-section-slide(title)` starts a new section (Aqua does **not** auto-fire
on level-1 headings — call it explicitly).

## Example

```typst
#import "@preview/touying:0.7.3": *
#import themes.aqua: *

#show: aqua-theme.with(
  aspect-ratio: "16-9",
  config-info(
    title: [Title], subtitle: [Subtitle],
    author: [Authors], date: datetime.today(),
    institution: [Institution],
  ),
)

#title-slide()
#outline-slide()

= The Section
== Slide Title
#lorem(40)

#focus-slide[
  Another variant with primary color in background...
]

== Summary
#slide(self => [
  #align(center + horizon)[
    #set text(size: 3em, weight: "bold", fill: self.colors.primary)
    THANKS FOR ALL
  ]
])
```

See [`examples/05-aqua/05-aqua.typ`](./examples/05-aqua/05-aqua.typ).

## Pitfalls

- `outline-slide(enum-args: (...))` lets you forward args to the
  underlying `enum` (e.g. `enum-args: (numbering: "I.")`).
- `new-section-slide(title)` must be called explicitly — Aqua does not
  install an automatic `new-section-slide-fn`.
- The blue gradient background reads `self.colors.primary`; switch to
  e.g. `rgb("#5E8B65")` for a green-toned variant via `config-colors`.
