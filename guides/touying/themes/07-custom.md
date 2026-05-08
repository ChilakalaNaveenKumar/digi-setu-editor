# Custom Theme

> Source: <https://touying-typ.github.io/docs/themes/custom>

If none of the built-in themes (`simple`, `metropolis`, `dewdrop`,
`university`, `aqua`, `stargazer`) fits, you have two options:

1. **Extend an existing theme** — copy a theme file locally and modify it.
2. **Build a new theme from scratch** — implement your own
   `xxx-theme(..)` function.

Both approaches are described in detail in the [Build Your Own Theme
tutorial](../tutorial/07-build-your-own-theme.md).

## Quick modifications

For minor tweaks, you do not need to copy the theme. Override individual
settings inline:

```typst
#import "@preview/touying:0.7.3": *
#import themes.metropolis: *

#show: metropolis-theme.with(
  aspect-ratio: "16-9",
  config-colors(primary: rgb("#1a6b8a")),  // override primary color
  footer: self => self.info.author,         // change footer content
  config-info(
    title: [My Presentation],
    author: [Author Name],
    date: datetime.today(),
  ),
)

#title-slide()

= Section
== Slide
Content with the custom color.
```

## Copying a theme locally

For deeper structural changes:

1. Download the relevant file from `themes/` in the
   [Touying repository](https://github.com/touying-typ/touying/tree/main/themes)
   — e.g. `themes/metropolis.typ`.
2. Change the import at the top from
   `#import "../src/exports.typ": *` to
   `#import "@preview/touying:0.7.3": *`.
3. Import the local copy instead of the built-in theme.

```typst
#import "@preview/touying:0.7.3": *
#import "metropolis.typ": *      // your local copy

#show: metropolis-theme.with(
  aspect-ratio: "16-9",
  config-info(title: [Title]),
)
```

You can now freely edit `metropolis.typ` without affecting other projects.

## Example

See [`examples/07-custom/`](./examples/07-custom/) for a runnable example
that overrides the metropolis theme primary color and footer.

## Pitfalls

- Local theme files import Touying with the registry path
  (`@preview/touying:0.7.3`); the in-repo themes use the relative path
  (`../src/exports.typ`).
- When copying multiple themes, watch for name collisions — both export
  `slide`, `title-slide`, etc. Wrap each with
  `#import "metropolis.typ" as metropolis` to namespace them.
- Quick `config-colors(...)` / `config-info(...)` overrides are usually
  enough; only fork the file when you need to change the slide function
  bodies.
