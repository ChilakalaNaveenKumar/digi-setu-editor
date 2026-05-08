# `simple-theme` — Simple Theme

> Source: <https://touying-typ.github.io/docs/themes/simple>
>
> Originates from [Polylux](https://polylux.dev/book/themes/gallery/simple.html),
> created by Andreas Kröpelin.

A relatively straightforward theme — use it for simple slides and freely
incorporate features as you need them.

## Initialization

```typst
#import "@preview/touying:0.7.3": *
#import themes.simple: *

#show: simple-theme.with(
  aspect-ratio: "16-9",
  footer: [Simple slides],
)
```

## Parameters

`simple-theme.with(..)` accepts:

- **`aspect-ratio`** *(str, default `"16-9"`)* — `"16-9"` or `"4-3"`.
- **`header`** *(content / fn, default `utils.display-current-heading(setting: utils.fit-to-width.with(grow: false, 100%))`)* — header content. Pass a function `self => self.info.title` to compute from `self`.
- **`header-right`** *(default `self => self.info.logo`)* — right-side header.
- **`footer`** *(default `[]`)* — footer content. Function form supported.
- **`footer-right`** *(default `context utils.slide-counter.display() + " / " + utils.last-slide-number`)* — right-side footer.
- **`primary`** *(color, default `aqua.darken(50%)`)* — primary color.
- **`subslide-preamble`** — by default adds the subsection title to the slide.

## Slide function family

```typst
#centered-slide(section: ..)[ ... ]
```

A slide with content centered. The `section:` parameter can create a new
section.

```typst
#title-slide[ ... ]
```

Same as `centered-slide` — provided for Polylux compatibility.

```typst
#slide(
  config: (:),
  repeat: auto,
  setting: body => body,
  composer: cols,
)[ ... ]
```

The default slide with header / footer.

```typst
#focus-slide(foreground: ..., background: ...)[ ... ]
```

Used to draw attention. `foreground:` defaults to `white`, `background:`
defaults to `auto` (i.e. `self.colors.primary`).

## Example

```typst
#import "@preview/touying:0.7.3": *
#import themes.simple: *

#show: simple-theme.with(
  aspect-ratio: "16-9",
  footer: [Simple slides],
)

#title-slide[
  = Keep it simple!
  #v(2em)
  Alpha #footnote[Uni Augsburg] #h(1em)
  Bravo #footnote[Uni Bayreuth] #h(1em)
  Charlie #footnote[Uni Chemnitz] #h(1em)
  July 23
]

== First slide
#lorem(20)

#focus-slide[
  _Focus!_
  This is very important.
]

= Let's start a new section!
== Dynamic slide
Did you know that...
#pause
...you can see the current section at the top of the slide?
```

See [`examples/01-simple/01-simple.typ`](./examples/01-simple/01-simple.typ).

## Pitfalls

- The default `primary` is `aqua.darken(50%)` — a dark teal. Override
  with `config-colors(primary: ...)` rather than the `primary:` arg if
  you also want consistent secondary/tertiary colors.
- Footer / header functions receive **no** `self` automatically when
  passed inline — use `footer: self => self.info.author` to read from
  `self`.
