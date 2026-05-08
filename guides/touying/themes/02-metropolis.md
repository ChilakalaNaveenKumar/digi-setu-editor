# `metropolis-theme` — Metropolis Theme

> Source: <https://touying-typ.github.io/docs/themes/metropolis>
>
> Inspired by Matthias Vogelgesang's [Metropolis Beamer](https://github.com/matze/mtheme)
> theme; ported by [Enivex](https://github.com/Enivex).

Elegant, talk-friendly, and the most-used Touying theme for conference
presentations. **Recommended fonts:** Fira Sans + Fira Math.

## Initialization

```typst
#import "@preview/touying:0.7.3": *
#import themes.metropolis: *
#import "@preview/numbly:0.1.0": numbly

#show: metropolis-theme.with(
  aspect-ratio: "16-9",
  footer: self => self.info.institution,
  config-info(
    title: [Title], subtitle: [Subtitle],
    author: [Authors], date: datetime.today(),
    institution: [Institution],
    contact: [contact\@mail.com],
    logo: emoji.city,
  ),
)
#set heading(numbering: numbly("{1}.", default: "1.1"))
#title-slide()
```

## Parameters

`metropolis-theme.with(..)` accepts:

- **`aspect-ratio`** *(default `"16-9"`)*.
- **`align`** *(default `horizon`)* — vertical alignment of the slide content.
- **`header`** *(default `utils.display-current-heading(setting: utils.fit-to-width.with(grow: false, 100%))`)*.
- **`header-right`** *(default `self => self.info.logo`)*.
- **`footer`** *(default `[]`)*.
- **`footer-right`** *(default `context utils.slide-counter.display() + " / " + utils.last-slide-number`)*.
- **`footer-progress`** *(bool, default `true`)* — show the bottom progress bar.

## Color theme

```typc
config-colors(
  primary:           rgb("#eb811b"),
  primary-light:     rgb("#d6c6b7"),
  secondary:         rgb("#23373b"),
  neutral-lightest:  rgb("#fafafa"),
  neutral-dark:      rgb("#23373b"),
  neutral-darkest:   rgb("#23373b"),
)
```

Override with `config-colors(...)`.

## Slide function family

```typst
#title-slide(extra: none, ..args)
```

Reads from `self.info`. `extra:` displays additional information.

```typst
#slide(
  config: (:), repeat: auto,
  setting: body => body, composer: cols,
  // metropolis-specific
  title: auto, footer: auto, align: horizon,
)[ ... ]
```

```typst
#focus-slide[ ... ]
```

Background = `self.colors.primary-dark`.

```typst
#new-section-slide(short-title: auto, title)
```

Creates a new section slide with the given title.

## Example

```typst
#import "@preview/touying:0.7.3": *
#import themes.metropolis: *
#import "@preview/numbly:0.1.0": numbly

#show: metropolis-theme.with(
  aspect-ratio: "16-9",
  footer: self => self.info.institution,
  config-info(
    title: [Title],
    author: [Authors],
    date: datetime.today(),
    institution: [Institution],
    logo: emoji.city,
  ),
)
#set heading(numbering: numbly("{1}.", default: "1.1"))

#title-slide()

= Outline <touying:hidden>
#outline(title: none, indent: 1em, depth: 1)

= First Section
---
A slide without a title but with some *important* information.

== A long title
$ x_(n+1) = (x_n + a/x_n) / 2 $

= Second Section
#focus-slide[Wake up!]

== Simple Animation
We can use `#pause` to #pause display something later.

#show: appendix
= Appendix
---
Please pay attention to the current slide number.
```

See [`examples/02-metropolis/02-metropolis.typ`](./examples/02-metropolis/02-metropolis.typ).

## Pitfalls

- Without Fira Sans / Fira Math installed, fonts fall back to system
  defaults (still works, but the look is off).
- v0.7.3 added `outline-slide` to metropolis — earlier versions don't
  have it; pin `@preview/touying:0.7.3` if you rely on it.
- `align: horizon` (vertical centring) is the default — pass
  `align: top` if you want top-aligned slides.
