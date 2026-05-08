# `university-theme` — University Theme

> Source: <https://touying-typ.github.io/docs/themes/university>
>
> Courtesy of [Pol Dellaiera](https://github.com/drupol).

Aesthetically pleasing, three-column footer, top progress bar.

## Initialization

```typst
#import "@preview/touying:0.7.3": *
#import themes.university: *
#import "@preview/numbly:0.1.0": numbly

#show: university-theme.with(
  aspect-ratio: "16-9",
  config-info(
    title: [Title], subtitle: [Subtitle],
    author: [Authors], date: datetime.today(),
    institution: [Institution],
    contact: [contact\@mail.com],
    logo: emoji.school,
  ),
)
#set heading(numbering: numbly("{1}.", default: "1.1"))
#title-slide()
```

## Parameters

`university-theme.with(..)` accepts:

- **`aspect-ratio`** *(default `"16-9"`)*.
- **`progress-bar`** *(bool, default `true`)* — top progress bar.
- **`header`** *(default `utils.display-current-heading(level: 2)`)*.
- **`header-right`** *(default `self => self.info.logo`)*.
- **`footer-columns`** *(default `(25%, 1fr, 25%)`)* — widths of the three footer columns.
- **`footer-a`** *(default `self => self.info.author`)* — first column.
- **`footer-b`** *(default `self => if self.info.short-title == auto { self.info.title } else { self.info.short-title }`)*.
- **`footer-c`** *(default below)*:

```typst
self => {
  h(1fr)
  utils.display-info-date(self)
  h(1fr)
  context utils.slide-counter.display() + " / " + utils.last-slide-number
  h(1fr)
}
```

## Color theme

```typc
config-colors(
  primary:          rgb("#04364A"),
  secondary:        rgb("#176B87"),
  tertiary:         rgb("#448C95"),
  neutral-lightest: rgb("#ffffff"),
  neutral-darkest:  rgb("#000000"),
)
```

## Slide function family

```typst
#title-slide(logo: none, authors: none, ..args)
```

Reads from `self.info`. `authors:` accepts an array (e.g.
`authors: ([Author A], [Author B])`).

```typst
#slide(
  config: (:), repeat: auto,
  setting: body => body, composer: cols,
  // university-specific
  title: none,
)[ ... ]
```

`title` defaults to the current section title.

### Focus slide

```typst
#focus-slide(background-img: ..., background-color: ...)[ ... ]
```

### Matrix slide

```typst
#matrix-slide(columns: ..., rows: ...)[ ... ][ ... ]
```

Refer to the [Polylux docs](https://polylux.dev/book/themes/gallery/university.html).

## Example

```typst
#import "@preview/touying:0.7.3": *
#import themes.university: *
#import "@preview/numbly:0.1.0": numbly

#show: university-theme.with(
  aspect-ratio: "16-9",
  config-info(
    title: [Title], subtitle: [Subtitle],
    author: [Authors], date: datetime.today(),
    institution: [Institution],
    logo: emoji.school,
  ),
)
#set heading(numbering: numbly("{1}.", default: "1.1"))

#title-slide(authors: ([Author A], [Author B]))

= The Section
== Slide Title
#lorem(40)

#focus-slide[
  Another variant with primary color in background...
]

#matrix-slide[ left ][ middle ][ right ]
#matrix-slide(columns: 1)[ top ][ bottom ]
#matrix-slide(columns: (1fr, 2fr, 1fr), ..(lorem(8),) * 9)
```

See [`examples/04-university/04-university.typ`](./examples/04-university/04-university.typ).

## Pitfalls

- `title-slide(authors: ...)` expects an **array** of names, even for one
  author: `authors: ([Solo Author],)`.
- Default `slide-level: 2` — level-1 = section, level-2 = slide title.
- `matrix-slide` is laid out by `grid` underneath; pass `columns:` and
  `rows:` like a Typst grid.
