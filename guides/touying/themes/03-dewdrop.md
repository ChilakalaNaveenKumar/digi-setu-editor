# `dewdrop-theme` — Dewdrop Theme

> Source: <https://touying-typ.github.io/docs/themes/dewdrop>
>
> Inspired by Zhibo Wang's [BeamerTheme](https://github.com/zbowang/BeamerTheme);
> ported by [OrangeX4](https://github.com/OrangeX4).

Elegantly designed navigation: choose between two modes — `sidebar` and
`mini-slides`.

## Initialization

```typst
#import "@preview/touying:0.7.3": *
#import themes.dewdrop: *
#import "@preview/numbly:0.1.0": numbly

#show: dewdrop-theme.with(
  aspect-ratio: "16-9",
  footer: self => self.info.institution,
  navigation: "mini-slides",
  config-info(
    title: [Title], subtitle: [Subtitle],
    author: [Authors], date: datetime.today(),
    institution: [Institution],
    contact: [contact\@mail.com],
  ),
)
#title-slide()
#outline-slide()
```

## Parameters

`dewdrop-theme.with(..)` accepts:

- **`navigation`** *(str, default `"mini-slides"`)* — `"mini-slides"` or `"sidebar"`.
- **`mini-slides`** *(dict, default values: `(height: 4em, x: 2em, display-section: false, display-subsection: true, short-heading: true)`)* — settings for mini-slides nav.

  Sub-parameters:
  - `height` *(default `2em`)* — height of the mini-slides bar.
  - `x` *(default `2em`)* — x-axis padding.
  - `section` *(default `false`)* — show slides between section and first subsection.
  - `subsection` *(default `true`)* — split mini-slides per subsection (squashes if `false`).
  - `display-section` / `display-subsection` / `short-heading` — display flags.

- **`alpha`** *(default `70%`)* — transparency level for inactive nav entries.

The Dewdrop theme also exports an `#alert[..]` function. Combine with
`#show strong: alert` to make `*emphasis*` use the primary colour.

## Color theme

```typc
config-colors(
  neutral-darkest:  rgb("#000000"),
  neutral-dark:     rgb("#202020"),
  neutral-light:    rgb("#f3f3f3"),
  neutral-lightest: rgb("#ffffff"),
  primary:          primary,
)
```

## Slide function family

```typst
#title-slide(extra: none, ..args)
#slide(config: (:), repeat: auto, setting: body => body, composer: cols)[ ... ]
#focus-slide[ ... ]
```

`focus-slide` background = `self.colors.primary`.

## Example

```typst
#import "@preview/touying:0.7.3": *
#import themes.dewdrop: *
#import "@preview/numbly:0.1.0": numbly

#show: dewdrop-theme.with(
  aspect-ratio: "16-9",
  footer: self => self.info.institution,
  navigation: "mini-slides",
  config-info(
    title: [Title], author: [Authors],
    date: datetime.today(), institution: [Institution],
  ),
)
#set heading(numbering: numbly("{1}.", default: "1.1"))

#title-slide()
#outline-slide()

= Section A
== Subsection A.1
$ x_(n+1) = (x_n + a/x_n) / 2 $

== Subsection A.2
A slide without a title but with *important* infos.

= Section B
== Subsection B.1
#lorem(80)

#focus-slide[Wake up!]

== Subsection B.2
We can use `#pause` to #pause display something later.

#show: appendix
= Appendix
== Appendix
Please pay attention to the current slide number.
```

See [`examples/03-dewdrop/03-dewdrop.typ`](./examples/03-dewdrop/03-dewdrop.typ).

## Pitfalls

- Dewdrop's `slide-level` is **3** by default — `=`, `==`, `===` map to
  section / subsection / subsubsection. Override with
  `config-common(slide-level: 2)` to get the more typical
  section / slide-title mapping.
- `navigation: "sidebar"` puts the section list on the left — looks
  great for short decks, cramped for long ones.
- Combine with `components.progressive-outline()` for a TOC slide.
