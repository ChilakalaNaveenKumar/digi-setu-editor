# `read()` — Plain Text and Bytes

`read` is the lowest-level loader: it returns the raw contents of a file
as either a UTF-8 string or as bytes.

## Signature

```text
read(
  path:     str,                              // file path
  encoding: none | "utf8" = "utf8",           // none → bytes
) -> str | bytes
```

## Two modes

### Text (default)

```typst
#let html = read("snippet.html")
#raw(html, lang: "html", block: true)
```

The file is decoded as UTF-8 and returned as a `str`. Errors if the
bytes are not valid UTF-8 — use `encoding: none` for binary files.

### Bytes

```typst
#let png = read("logo.png", encoding: none)
#image(png, format: "png", alt: "Acme logo")
```

When you pass `encoding: none`, you get raw `bytes`. This is the right
mode for:

- Feeding binary assets to [`image`](../visualize/06-image.md),
  [`json`](./03-json.md), [`cbor`](./01-cbor.md), and friends without an
  intermediate decoding step.
- Computing hashes, sizes, or other byte-level inspection.

## Pipelining with other loaders

`read(... , encoding: none)` followed by another loader is the
standard way to inject preprocessing between disk and parser:

```typst
#let raw  = read("config.json")
#let cfg  = json(bytes(raw.replace("$ENV$", "production")))
```

For SVG you can string-replace colors before rendering:

```typst
#let svg  = read("logo.svg")
#image(bytes(svg.replace("#ff0000", green.to-hex())))
```

## Path resolution

Paths follow Typst's normal rules: relative to the current source file,
absolute, or project-relative (`/path/from/root.typ`). See
[Paths](https://typst.app/docs/reference/syntax/#paths).

## Tips

- For configuration that needs to be queried from the CLI, prefer
  [`metadata`](../introspection/05-metadata.md) inside the document over
  side-loading via `read`.
- Reading the same file in many places is fine — Typst caches files
  across the document.
