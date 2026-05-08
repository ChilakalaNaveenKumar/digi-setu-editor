# External — Pdfpc

> Source: <https://touying-typ.github.io/docs/external/pdfpc>
>
> Tool: <https://pdfpc.github.io/>

[pdfpc](https://pdfpc.github.io/) is a "Presenter Console with multi-
monitor support for PDF files". You feed it a PDF + a `.pdfpc` JSON
metadata file, and it gives you PowerPoint-class presenter features
(timer, notes, two-screen mode, transitions).

## Adding metadata

Touying remains compatible with [Polylux](https://polylux.dev/book/external/pdfpc.html)
to avoid PDFPC API conflicts.

Per-slide note:

```typst
#pdfpc.speaker-note("This is a note that only the speaker will see.")
```

Top-of-file pdfpc configuration:

```typst
#pdfpc.config(
  duration-minutes: 30,
  start-time: datetime(hour: 14, minute: 10, second: 0),
  end-time:   datetime(hour: 14, minute: 40, second: 0),
  last-minutes: 5,
  note-font-size: 12,
  disable-markdown: false,
  default-transition: (
    type: "push",
    duration-seconds: 2,
    angle: ltr,
    alignment: "vertical",
    direction: "inward",
  ),
)
```

Refer to the [Polylux pdfpc docs](https://polylux.dev/book/external/pdfpc.html)
for the full set of configuration keys.

## Exporting the `.pdfpc` file

Touying writes the metadata into the PDF as a label. Extract it with
`typst query`:

```sh
typst query --root . ./example.typ --field value --one "<pdfpc-file>" > ./example.pdfpc
```

Now run pdfpc on the pair:

```sh
pdfpc example.pdf
# pdfpc auto-detects ./example.pdfpc
```

## Polylux compatibility

If you also want pure-Polylux files to support direct export, add:

```typst
#import "@preview/touying:0.7.3"
#context touying.pdfpc.pdfpc-file(here())
```

This re-exposes Touying's pdfpc-file generator from a Polylux deck.

## Example

See [`examples/04-pdfpc/04-pdfpc.typ`](./examples/04-pdfpc/04-pdfpc.typ).

## Pitfalls

- `pdfpc.config(...)` must be called **once** at the top of the file,
  before the theme show rule.
- `pdfpc.speaker-note("text")` (with parentheses + string) is the
  Polylux-compatible form. Touying also accepts the content form
  `#speaker-note[...]` — they are different APIs.
- The `<pdfpc-file>` label is generated automatically; no need to add
  it yourself.
- pdfpc 4.6+ is recommended for stable Typst-PDF support.
