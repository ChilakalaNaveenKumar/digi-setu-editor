# `image()` — Embedding Raster and Vector Graphics

`image` embeds a graphic file (or raw bytes) into the document. By default
it is **block-level**; wrap it in a [`box`](../layout/05-box.md) to flow
inline.

## Signature

```text
image(
  source:  str | bytes,                                  // path or raw data
  format:  auto | str | dictionary = auto,
  width:   auto | relative = auto,
  height:  auto | relative | fraction = auto,
  alt:     none | str = none,
  page:    int = 1,                                      // PDF source only
  fit:     "cover" | "contain" | "stretch" = "cover",
  scaling: auto | "smooth" | "pixelated" = auto,
  icc:     auto | str | bytes = auto,
) -> content
```

## Supported formats

`"png"`, `"jpg"`, `"gif"` (rendered as a still frame), `"webp"`, `"svg"`,
`"pdf"`. Format is auto-detected from the file extension or magic bytes;
override with `format:` when passing raw bytes whose format isn't obvious.

For **raw pixel data** pass `format` as a dictionary:

```typst
#image(
  bytes(my-pixels),
  format: (encoding: "rgba8", width: 16, height: 16),
)
```

`encoding` is one of `"rgb8"`, `"rgba8"`, `"luma8"`, `"lumaa8"`. The byte
length must equal `width × height × channels`.

## PDF-as-image caveats

When you embed a PDF (`source: "diagram.pdf"`):

- The embedded PDF version must be ≤ your export target version.
- PDF/A-3 and PDF/UA-1 export does **not** support PDF images. Use SVG
  instead in those cases.
- Password-protected PDFs are rejected.
- Tags inside the PDF are dropped — supply `alt:` for accessibility.

Use `page: N` to pick a page from a multi-page PDF.

## Sizing and `fit`

When you give both `width` and `height`, the image must decide what to do
with the leftover space:

| `fit` value  | Behaviour                                                                    |
| ------------ | ---------------------------------------------------------------------------- |
| `"cover"` (default) | Fills the box, cropping along one axis if needed. Aspect ratio kept. |
| `"contain"`  | Fits entirely inside the box. One axis may be smaller than requested.        |
| `"stretch"`  | Fills exactly, distorting aspect ratio if necessary.                         |

If you only set one of `width`/`height`, the other is computed from the
image's intrinsic aspect ratio.

## Scaling hint

`scaling: "smooth"` (the default for PNG export) uses bilinear filtering;
`"pixelated"` is best for pixel art and fixed-grid screenshots. The hint is
respected by some viewers.

## Accessibility

Always supply `alt:` for raster/decorative-vector images that convey
information. When wrapped in a `figure(...)`, set `alt` on the **image**
unless the image plus surrounding labels form a single semantic unit (in
which case set `alt` on the figure).

## Inline images

`image` is block-level by default. Use a `box` to keep it inline (e.g.
inline icons):

```typst
A logo: #box(image("logo.svg", height: 1em, alt: "Acme logo")) is inline.
```

## Loading bytes (and modifying SVG)

You can read a file as `bytes` and pass it to `image`. This lets you
preprocess SVG strings before rendering:

```typst
#let svg = read("diagram.svg")
#image(bytes(svg.replace("#2B80FF", green.to-hex())))
```

`image.decode(...)` is **deprecated** since 0.13 — pass bytes directly to
`image(...)` instead.
