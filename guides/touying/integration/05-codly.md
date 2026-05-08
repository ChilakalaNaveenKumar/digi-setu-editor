# Integration — Codly

> Source: <https://touying-typ.github.io/docs/integration/codly>
>
> Package: [`codly`](https://github.com/Dherse/codly) v1.3.0
> + [`codly-languages`](https://github.com/Dherse/codly-languages) v0.1.10

[Codly](https://github.com/Dherse/codly) gives Typst's `raw` blocks a
beautiful look — language icons, line numbers, syntax highlighting,
zebra striping. Touying needs a small bit of setup because it re-renders
content on every subslide.

## Setup

`codly` maintains per-page state. To make sure that state is restored
before each Touying slide is drawn, pass the codly initialization as a
`preamble`:

```typst
#import "@preview/touying:0.7.3": *
#import themes.simple: *
#import "@preview/codly:1.3.0": *
#import "@preview/codly-languages:0.1.10": *

#show: codly-init.with()
#show: simple-theme.with(
  aspect-ratio: "16-9",
  config-common(preamble: {
    codly(languages: codly-languages)
  }),
)

== First Slide
#raw(lang: "rust", block: true, ```
pub fn main() {
  println!("Hello, world!");
}
```.text)
```

`#show: codly-init.with()` installs the codly show rules. The
`config-common(preamble: ...)` re-runs `codly(languages: codly-
languages)` at the start of each slide, restoring the language map and
counter.

## Animated code blocks — `touying-raw`

`#pause` does **not** work inside a `raw {}` block (raw blocks are
opaque to Touying's metadata injection). Use `touying-raw` instead — it
recognises `// pause` and `// meanwhile` comment markers as animation
steps:

```typst
#import "@preview/touying:0.7.3": *
#import themes.simple: *

#show: simple-theme.with(aspect-ratio: "16-9")

== Animated Raw Block
#touying-raw(lang: "python", ```
print("Step 1")
// pause
print("Step 2")
// pause
print("Step 3")
```)
```

`touying-raw(lang: ..., ```...```)` returns a `raw` block where each
`// pause` triggers a subslide. Comment markers stay readable in the
source.

## Codly + animation together

Combine `touying-raw` with the codly preamble to get the full styled
look:

```typst
#show: simple-theme.with(
  aspect-ratio: "16-9",
  config-common(preamble: {
    codly(languages: codly-languages)
  }),
)

== Animated Code
#touying-raw(lang: "python", ```
def greet(name):
// pause
    return f"Hello, {name}!"
// pause
print(greet("World"))
```)
```

## Example

See [`examples/05-codly/05-codly.typ`](./examples/05-codly/05-codly.typ).

## Pitfalls

- Forgetting the `preamble` causes codly to forget its language map
  starting from the second slide — code looks like plain text.
- `// pause` markers must be on their own line and preceded by `//`
  (not `#`). They are stripped from the rendered output.
- For multi-line reveals, `touying-raw` reveals **lines** between
  consecutive markers — to reveal one line at a time put a marker after
  every line.
- `touying-raw` doesn't currently support `// only` / `// uncover` —
  use callback-style with manual line-by-line `raw` blocks if you need
  that level of control.
