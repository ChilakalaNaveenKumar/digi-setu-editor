# External — Typst Preview in Tinymist

> Source: <https://touying-typ.github.io/docs/external/typst-preview>
>
> Extension: [Tinymist for VS Code](https://marketplace.visualstudio.com/items?itemName=myriad-dreamin.tinymist)

The [Tinymist](https://github.com/Myriad-Dreamin/tinymist) extension for
VS Code provides an excellent **slide preview mode**, perfect for
authoring Touying decks.

## Quick start

Open your `.typ` slide file in VS Code, then either:

- **`Ctrl/Cmd + Shift + P` → `Typst Preview: Preview current file in slide mode`** — opens the slide preview in a side panel.
- **`Ctrl/Cmd + Shift + P` → `Typst Preview: Preview current file in browser and slide mode`** — opens the slide mode in your browser.

In the browser version, press `F11` to enter fullscreen — that turns it
into a real presentation.

## Why this is useful for Touying

Tinymist's preview is **SVG-based**. That means it can play GIF
animations natively (which you cannot do with PDF), so dynamic diagrams
look exactly as the audience will see them.

It is also **incremental** — only changed slides re-render. With
Touying's already-fast compilation that means edits show up
near-instantly.

## Workflow

1. Edit `main.typ`.
2. Trigger the slide-mode preview.
3. Use arrow keys to navigate.
4. Iterate; the preview updates as you save.
5. When ready, run `typst compile main.typ main.pdf` for the final PDF
   (or feed the file to `touying-exporter` for HTML / PPTX — see
   [`01-touying-exporter.md`](./01-touying-exporter.md)).

## Pitfalls

- Tinymist needs the **typst-preview** companion extension installed
  separately on some setups; check the marketplace listing.
- The browser slide mode loads SVGs over HTTP; very large decks (200+
  slides) may take a moment to first-render.
- In-VS-Code preview pane has a fixed aspect ratio that doesn't always
  match `aspect-ratio: "16-9"` — use the browser variant for fidelity
  checks.
