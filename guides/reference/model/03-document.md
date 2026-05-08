# `document` — root element + PDF metadata

`document` is the implicit root element wrapping every Typst document. You **never construct** it yourself — you only configure it via `set document(...)` to embed metadata that ends up in the exported PDF (or HTML head).

```typst
#set document(title: [My Paper])
```

Nothing renders to the page; the metadata lands in the PDF properties / browser tab.

## Settable fields

| Field         | Type                              | Default | Use                                    |
| ------------- | --------------------------------- | ------- | -------------------------------------- |
| `title`       | `none` \| `content`              | `none`  | PDF window / browser tab title         |
| `author`      | `str` \| `array<str>`            | `()`    | One or more author names               |
| `description` | `none` \| `content`              | `none`  | Long-form summary                      |
| `keywords`    | `str` \| `array<str>`            | `()`    | For PDF search / indexing              |
| `date`        | `none` \| `auto` \| `datetime`   | `auto`  | Creation date in PDF metadata          |

PDF viewers only support **plain text titles**, so rich `content` is flattened during conversion (math, formatting, etc. become text or are stripped).

## `date` behaviour

- `auto` (default): the current date when compiling.
- `none`: **no creation date** in the PDF — useful for **byte-reproducible** builds.
- `datetime(...)`: a fixed date you control. Year must be `>= 0` for PDF embedding.

## Where you can place it

`set document(...)` must be at top level (or inside a non-layout container — e.g. a code block at the top of the file). It will **error** inside layout containers like `#figure`, `#grid`, `#block`, `#columns`, etc.:

```text
error: set rule must not occur inside of any layout container
```

## Pitfalls

- **Title metadata is text-only** in the final PDF. Don't expect `set document(title: $E = m c^2$)` to render math in the viewer's tab — it'll be approximated.
- **Don't confuse `document.title` with `title` element.** The `title` element (separate page) is what visibly renders the title on the page; `document.title` only sets PDF metadata. They can be linked: `#title()` with no body falls back to `document.title`.
- **Required for PDF/UA.** Accessible PDF export (PDF/UA) **requires** a non-empty `title`. Always set one for production documents.
- **Reproducible PDFs.** If you need byte-identical PDFs across builds, set `date: none` (or a fixed `datetime`) AND ensure no other source of variability (e.g. `sys.inputs`, file timestamps).

## Examples (compile-verified)

- `examples/03-document/01-document-metadata.typ` — sets all five metadata fields, documents the layout-container restriction, and explains how to verify in a PDF viewer.

## Reference

- Official: https://typst.app/docs/reference/model/document/
- `title` element (visible title on the page): https://typst.app/docs/reference/model/title/
- `datetime`: https://typst.app/docs/reference/foundations/datetime/
