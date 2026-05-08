# External — Pympress

> Source: <https://touying-typ.github.io/docs/external/pympress>
>
> Tool: <https://github.com/Cimbali/pympress>

[Pympress](https://github.com/Cimbali/pympress) is a PDF presentation
tool for dual-screen setups. Highly configurable, fully-featured, and
portable.

## Speaker notes

Pympress reads speaker notes from the second half of the slide when you
enable Touying's *show-notes-on-second-screen* mode:

```typst
#import "@preview/touying:0.7.3": *
#import themes.university: *

#show: university-theme.with(
  aspect-ratio: "16-9",
  config-common(show-notes-on-second-screen: right),
)

= Animation
== Simple Animation
We can use `#pause` to #pause display something later.
#pause
Just like this.

#meanwhile
Meanwhile, #pause we can also use `#meanwhile` to #pause display other content synchronously.

#speaker-note[
  + This is a speaker note.
  + You won't see it unless you use `config-common(show-notes-on-second-screen: right)`
]
```

`config-common(show-notes-on-second-screen: right)` widens each slide
horizontally and places the speaker notes on the right half. Pympress
then shows only the left half on the audience screen, and the right
half on the presenter screen.

Other valid values: `left`, `top`, `bottom`.

## Workflow

1. Compile the Typst file: `typst compile main.typ main.pdf`.
2. Open in Pympress: `pympress main.pdf`.
3. Pympress detects the dual-half layout and routes the halves correctly.

## Example

See [`../tutorial/dynamic/examples/01-simple/01-simple.typ`](../tutorial/dynamic/examples/01-simple/01-simple.typ)
plus the speaker-note variant in
`../tutorial/04-settings.md` for a runnable file.

## Pitfalls

- `show-notes-on-second-screen: right` doubles the slide width, so layout
  needs to assume half-width text. For best results, use a theme that
  honours `self.page.width`.
- `#speaker-note[...]` placed *between* slides used to create a "ghost"
  empty slide; v0.7.3 fixed this — `#speaker-note[]` always attaches to
  the previous slide regardless of how that slide was created.
- Pympress respects PDFPC metadata too — see
  [`04-pdfpc.md`](./04-pdfpc.md) if you need timing or transition info.
