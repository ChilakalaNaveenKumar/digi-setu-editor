# `stargazer-theme` — Stargazer Theme

> Source: <https://touying-typ.github.io/docs/themes/stargazer>
>
> Originally created by [Coekjan](https://github.com/Coekjan/) for
> [touying-buaa](https://github.com/Coekjan/touying-buaa).

Aesthetically pleasing, versatile theme suitable for everyday use, with a
four-column footer (author, date, title, slide #).

## Initialization

```typst
#import "@preview/touying:0.7.3": *
#import themes.stargazer: *
#import "@preview/numbly:0.1.0": numbly

#show: stargazer-theme.with(
  aspect-ratio: "16-9",
  config-info(
    title: [Stargazer in Touying: Customize Your Slide Title Here],
    subtitle: [Customize Your Slide Subtitle Here],
    author: [Authors], date: datetime.today(),
    institution: [Institution],
    contact: [contact\@mail.com],
    logo: emoji.school,
  ),
)
#set heading(numbering: numbly("{1}.", default: "1.1"))
#title-slide()
#outline-slide()
```

## Parameters

`stargazer-theme.with(..)` accepts:

- **`aspect-ratio`** *(default `"16-9"`)*.
- **`align`** *(default `horizon`)*.
- **`alpha`** *(default `20%`)* — slide background transparency.
- **`title`** *(default `utils.display-current-heading()`)* — header content.
- **`progress-bar`** *(bool, default `true`)* — bottom progress bar.
- **`footer-columns`** *(default `(25%, 25%, 1fr, 5em)`)* — widths of the four footer columns.
- **`footer-a`** *(default `self => self.info.author`)*.
- **`footer-b`** *(default `self => utils.display-info-date(self)`)*.
- **`footer-c`** *(default `self => if self.info.short-title == auto { self.info.title } else { self.info.short-title }`)*.
- **`footer-d`** *(default `context utils.slide-counter.display() + " / " + utils.last-slide-number`)*.

## Color theme

```typc
config-colors(
  primary:           rgb("#005bac"),
  primary-dark:      rgb("#004078"),
  secondary:         rgb("#ffffff"),
  tertiary:          rgb("#005bac"),
  neutral-lightest:  rgb("#ffffff"),
  neutral-darkest:   rgb("#000000"),
)
```

## Slide function family

```typst
#title-slide(extra: none, ..args)
#slide(
  config: (:), repeat: auto,
  setting: body => body, composer: cols,
  // stargazer-specific
  title: auto, footer: auto, align: horizon,
)[ ... ]
#outline-slide[ ... ]
#focus-slide[ ... ]
#new-section-slide(short-title: auto, title)
```

`focus-slide` background = `self.colors.primary-dark`.

Stargazer also provides a `#tblock(title: ...)[...]` block for theorem-
style highlights.

## Example

```typst
#import "@preview/touying:0.7.3": *
#import themes.stargazer: *
#import "@preview/numbly:0.1.0": numbly

#show: stargazer-theme.with(
  aspect-ratio: "16-9",
  config-info(
    title: [Stargazer in Touying],
    subtitle: [Customize Your Slide Subtitle Here],
    author: [Authors], date: datetime.today(),
    institution: [Institution],
    logo: emoji.school,
  ),
)
#set heading(numbering: numbly("{1}.", default: "1.1"))

#title-slide()
#outline-slide()

= Section A
== Subsection A.1
#tblock(title: [Theorem])[
  A simple theorem.
  $ x_(n+1) = (x_n + a / x_n) / 2 $
]
== Subsection A.2
A slide without a title but with *important* information.

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

See [`examples/06-stargazer/06-stargazer.typ`](./examples/06-stargazer/06-stargazer.typ).

## Pitfalls

- `tblock(title: ..)` is a Stargazer extension — not exported by other
  themes. For cross-theme theorem support, see
  [`../integration/06-theorion.md`](../integration/06-theorion.md).
- Default `slide-level: 2` — `=` = section, `==` = subsection / slide.
- `info.short-title` defaults to `auto` (= `info.title`); set
  `config-info(short-title: [Short])` for a shorter footer label.
