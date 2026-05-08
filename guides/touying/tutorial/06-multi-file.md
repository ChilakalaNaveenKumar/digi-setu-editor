# 06 — Multi-File Architecture

> Source: <https://touying-typ.github.io/docs/tutorials/multi-file>

For decks with tens or hundreds of pages, split the project into three files
to keep `main.typ` clean while still benefiting from incremental compilation.

## Configuration / content separation

Three files: `globals.typ`, `main.typ`, `content.typ`.

### `globals.typ` — shared imports / utilities

```typst
// globals.typ
#import "@preview/touying:0.7.3": *
#import themes.university: *

// Custom helpers shared by every content file
#let alert-box(body) = block(
  fill: red.lighten(80%),
  inset: .5em,
  radius: .25em,
  body,
)
```

### `main.typ` — entry point with theme + `#include`

```typst
// main.typ
#import "/globals.typ": *

#show: university-theme.with(
  aspect-ratio: "16-9",
  config-info(
    title: [Title],
    subtitle: [Subtitle],
    author: [Authors],
    date: datetime.today(),
    institution: [Institution],
    contact: [contact\@mail.com],
    logo: emoji.school,
  ),
)

#include "content.typ"
```

### `content.typ` — actual slides

```typst
// content.typ
#import "/globals.typ": *

= The Section
== Slide Title
Hello, Touying!

#focus-slide[
  Focus on me.
]
```

## Why three files?

`globals.typ` is imported by **both** `main.typ` and `content.typ`. If we
inlined the theme show rule into `globals.typ` we would have a circular
dependency, because applying `#show: theme(...)` requires `content.typ` to
already exist.

Separating concerns also lets you switch themes by editing just `main.typ`,
without touching content.

## Multiple sections

Move content into a `sections/` directory:

```
project/
├── globals.typ
├── main.typ
└── sections/
    ├── content.typ
    ├── another-section.typ
    └── ...
```

```typst
// main.typ
#import "/globals.typ": *
#show: university-theme.with(/* ... */)

#include "sections/content.typ"
#include "sections/another-section.typ"
```

```typst
// sections/content.typ
#import "/globals.typ": *

= The Section
== Slide Title
Hello, Touying!
#focus-slide[Focus on me.]
```

## Example

See [`examples/06-multi-file/`](./examples/06-multi-file/) for a runnable
trio of files (`globals.typ`, `main.typ`, `content.typ`) you can compile
together.

## Pitfalls

- Use absolute imports (`#import "/globals.typ"`) rather than relative
  ones — Typst resolves `/` against the project root, so it works from
  any nested file.
- `#include` evaluates the file's content in the *current* show-rule
  context. `#import` only brings symbols into scope.
- Touying re-evaluates each slide multiple times (once per subslide), so
  expensive computations in `globals.typ` should be wrapped in `let` once.
