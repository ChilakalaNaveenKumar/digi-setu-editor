# `pdfpc` — Pdfpc Presenter Metadata

> Source: [src/pdfpc.typ](https://github.com/touying-typ/touying/blob/main/src/pdfpc.typ)

The `pdfpc` module produces JSON metadata compatible with
[pdfpc](https://pdfpc.github.io/) — a multi-monitor PDF presenter
console. Touying writes the metadata as a labelled element inside the
PDF; you extract it with `typst query`.

## `pdfpc.config(..keys)`

Top-of-file pdfpc configuration. Common keys:

```typst
#pdfpc.config(
  duration-minutes: 30,
  start-time:       datetime(hour: 14, minute: 10, second: 0),
  end-time:         datetime(hour: 14, minute: 40, second: 0),
  last-minutes:     5,
  note-font-size:   12,
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

See the [Polylux pdfpc docs](https://polylux.dev/book/external/pdfpc.html)
for the full key set (Touying mirrors the Polylux API for compat).

## `pdfpc.speaker-note(text)`

Per-slide speaker note in the Polylux-compatible (string-arg) form.
For Touying-native content-style notes, use `#speaker-note[...]`
instead — they live in the same metadata channel.

```typst
#pdfpc.speaker-note("Reminder: spend 2 min on this slide.")
```

## `pdfpc.pdfpc-file(here())`

Polylux-compat helper — when called from inside a Polylux deck, exposes
the same `<pdfpc-file>` label that Touying generates by default. Useful
if you want a Polylux-style file to also work with Touying's pdfpc
export workflow:

```typst
#import "@preview/touying:0.7.3"
#context touying.pdfpc.pdfpc-file(here())
```

## Exporting the JSON

```sh
typst query --root . ./example.typ --field value --one "<pdfpc-file>" > ./example.pdfpc
```

Touying always emits the `<pdfpc-file>` label (you don't have to call
`pdfpc-file` yourself in a pure Touying deck) — controlled by
`config-common(enable-pdfpc: true)` (the default).

## Disabling pdfpc emission

```typst
config-common(enable-pdfpc: false)
```

Useful if you don't use pdfpc and want a slightly smaller PDF.

## Pitfalls

- `pdfpc.config(...)` accepts a flat set of named args — there is no
  nested grouping (unlike `config-common`).
- `pdfpc.speaker-note("text")` (string arg) and `#speaker-note[...]`
  (content) are different APIs but emit equivalent JSON.
- Run `typst query` only after the `.typ` compiles cleanly — the label
  is only present in valid output.

## See also

- [`../../external/04-pdfpc.md`](../../external/04-pdfpc.md) — pdfpc
  workflow tutorial.
- [`../../external/03-pympress.md`](../../external/03-pympress.md) —
  alternative dual-screen presenter.
