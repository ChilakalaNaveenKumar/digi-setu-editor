# HTML – Overview and the `html` Module

> **Status: experimental.** HTML export is **active development**
> behind a feature flag. Don't use it for production. Track progress
> at the [HTML export tracking issue](https://github.com/typst/typst/issues/5512).

## What HTML export is for

HTML files describe a document **structurally**. Typst's HTML output
captures the structure of your input and emits semantic HTML that's
accessible, human-readable, and editable by hand or by downstream
tools.

This contrasts with PDF, PNG, and SVG — those output formats render
a fully laid-out, *visual* document. Because HTML's job is different,
Typst can't just press a button and produce "perfect HTML" for an
existing PDF-oriented document. There isn't always a single correct
HTML representation.

The trade-off:

- HTML export is **semantic-first**. Text, headings, lists, tables,
  links, images all become semantic HTML.
- It is **not** "render to a fixed visual layout in HTML". For
  pixel-perfect web rendering of a layout-sensitive part of your
  document, use [`html.frame(...)`](./02-frame.md) which embeds an
  inline SVG of that piece.
- Typst currently emits **a single HTML file**. Multi-file output and
  fragment output are planned but not yet shipped.
- Typst does **not** emit CSS today. You bring your own. Future
  versions plan to optionally emit CSS based on existing set rules.

## Enabling HTML export

```bash
# Either pass the flag to enable the feature:
typst compile paper.typ --features html --format html paper.html

# …or set it in the environment:
TYPST_FEATURES=html typst compile paper.typ paper.html
```

`typst watch` with HTML enabled also spins up a small live-reloading
HTTP server. Useful flags:

| Flag             | Effect                                                     |
| ---------------- | ---------------------------------------------------------- |
| `--port N`       | Set the dev-server port (defaults to first free in 3000-3005). |
| `--no-reload`    | Skip the live-reload script injection.                     |
| `--no-serve`     | Disable the dev server entirely; just write the HTML file. |

In the **web app**, HTML can be enabled as an experimental feature
in your project settings.

## The `target()` switch

Use [`target()`](../foundations/27-target.md) to branch your code for
HTML vs other formats. The canonical use is in templates and show
rules: emit semantic HTML when targeting HTML, fall back to layout
content for PDF/PNG/SVG.

```typst
#let card(body) = {
  if target() == "html" {
    html.elem("article", attrs: (class: "card"), body)
  } else {
    block(stroke: 0.5pt, inset: 8pt, body)
  }
}
```

This is the cleanest way to share a single document between HTML
and PDF.

## The `html` module

| Definition                              | Purpose                                                              |
| --------------------------------------- | -------------------------------------------------------------------- |
| [`html.elem(tag, attrs, body)`](./01-elem.md)    | Emit a raw HTML element with arbitrary tag and attributes.    |
| [`html.frame(body)`](./02-frame.md)              | Inline-SVG a Typst-laid-out fragment into the HTML.            |
| [`html.typed`](./03-typed.md)                    | Typed wrappers around `elem` for every HTML element + attribute. |

## What you get out of the box

Without writing any `html.*` calls, Typst will already emit:

- `<html>`, `<head>`, `<title>` from the document metadata.
- `<h1>` for the `title` element; `<h2>`–`<h6>` for headings (note
  the **off-by-one** with PDF: `title` → `<h1>`; level-1 heading →
  `<h2>`; etc.).
- `<p>` for paragraphs.
- `<em>` / `<strong>` for `_emph_` / `*strong*`.
- `<ul>` / `<ol>` / `<dl>` for `list` / `enum` / `terms`.
- `<a>` for `link(...)`.
- `<table>`, `<thead>`, `<tfoot>`, `<tbody>` for `table(...)`.
- `<figure>` + `<figcaption>` for `figure(...)`.
- `<code>` and `<pre>` for `raw(...)`.
- `<img>` (or inline SVG) for `image(...)` with the `alt:` attribute
  populated.

So the simplest workflow is: *write idiomatic Typst markup, target
HTML*. Reach for `html.*` only when you need finer control or
HTML-only constructs (custom classes, embeds, schema, ARIA, etc.).

## When to drop into raw HTML

Use [`html.elem(...)`](./01-elem.md) when:

- You need a class, id, ARIA attribute, or data-* attribute.
- You want to wrap content in a tag without semantic meaning in
  Typst (`<aside>`, `<section class="callout">`, `<nav>`).
- You're targeting an HTML-only feature (audio/video, canvas, embeds).

Use [`html.frame(...)`](./02-frame.md) when:

- A region needs *layout fidelity* (positioning, font metrics,
  precise sizing) — figures, plots, vector diagrams.
- You're embedding a piece that would lose meaning if reflowed
  semantically.

Use [`html.typed`](./03-typed.md) when:

- You want autocomplete + parameter hints for raw HTML elements.
- You want Typst types (booleans, numbers, lengths) auto-converted
  to the right HTML attribute strings.
