# `html.frame` – Embed Laid-Out Content as Inline SVG

```typst
html.frame(body) -> content
```

Lays `body` out using **the same engine as PDF/SVG/PNG export**, then
embeds the result as an **inline `<svg>`** in the HTML output.

## When to use it

- A block of content that **relies on positioning, fonts, and
  precise sizing** to convey meaning — typically figures, plots,
  diagrams.
- A region you can't (yet) faithfully express in semantic HTML —
  e.g. complex math typesetting, charts with absolute positioning.
- You want the **exact** PDF/SVG visual to appear in the HTML
  output, no matter what the surrounding stylesheet does.

## When NOT to use it

- Plain prose, headings, lists, tables — these have semantic HTML
  equivalents and should be exported as such (better accessibility,
  reflow, copy-paste).
- Anything where you'd be happy with a browser's native flow.

## Behavior

- The body is rendered exactly as it would be for PDF/SVG/PNG.
- The result is wrapped in an `<svg>` element inline in the HTML
  document. No external file.
- **Text inside a frame is rasterized as glyph paths** — like SVG
  export. That means it's not selectable / extractable; if you need
  selectable text, keep the content out of the frame.
- Frames are accessible only insofar as the *whole frame* can carry
  alt text via the surrounding `figure(alt: ...)`. Treat the frame
  as a single graphic.

## Parameters

| Name   | Type     | Required | Notes                                        |
| ------ | -------- | -------- | -------------------------------------------- |
| `body` | content  | yes      | Content to lay out and embed as inline SVG.  |

## Recipe – embed a precise diagram inside a web article

```typst
#figure(
  html.frame(
    rect(
      width: 6cm, height: 4cm, fill: aqua.lighten(70%),
      align(center + horizon)[
        #stack(spacing: 8pt,
          text(weight: "bold", size: 14pt)[Customer],
          [arrow → Product])
      ],
    ),
  ),
  caption: [Customer journey overview.],
  alt: "Diagram with a labelled box pointing from Customer to Product.",
)
```

In HTML this becomes a `<figure>` with an inline `<svg>`. In PDF
it's a normal block-rendered figure.

## Pairing with `target()`

You don't need `target()` around `html.frame` — it's a no-op outside
HTML export (the body just renders normally in the surrounding
context). `html.frame` is itself the way to say "render exactly the
same way regardless of target".

## Caveats

- **Big frames balloon the HTML file.** Inline SVG is verbose.
  Consider whether a regular SVG file (`<img src="...svg">` via
  `html.elem` or `html.typed`) would be more efficient for content
  that's static and reusable across pages.
- **Browser font rendering** still applies to *non-frame* HTML
  content. Don't expect a frame's text to match the browser's text
  pixel-for-pixel — it's vector glyph paths.
