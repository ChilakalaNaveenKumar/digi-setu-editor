# `pdf.attach` – Embed a File in the Output PDF

```typst
pdf.attach(
  path,
  data: bytes,                       // optional; if omitted, read from path
  relationship: "source" | "data" | "alternative" | "supplement",
  mime-type: str,
  description: str,
) -> content
```

Attaches an external file to the output PDF. PDF readers expose
attachments through a file panel; some workflows (e.g. ZUGFeRD /
Factur-X invoices) use this mechanism to ship machine-readable data
alongside the visual document.

## Notes and limitations

- **PDF only.** This element is silently ignored when exporting to
  HTML, PNG, or SVG.
- **PDF/A-2 doesn't support attachments.** If you need attachments
  *and* archival conformance, target PDF/A-3 (or PDF/A-4f).
- The path is always required, even when you supply raw bytes via
  `data:`. The path is used as the filename advertised inside the
  PDF.

## Parameters

| Name           | Type                  | Required | Default | Notes                                                     |
| -------------- | --------------------- | -------- | ------- | --------------------------------------------------------- |
| `path`         | str                   | yes      | —       | File path (also used as the attachment's filename).       |
| `data`         | bytes                 | yes / partial | —  | Raw file data. If omitted, Typst reads from `path`.       |
| `relationship` | none / str            | no       | `none`  | Relationship to the document (PDF/A-3 only).              |
| `mime-type`    | none / str            | no       | `none`  | MIME type of the attached file.                           |
| `description`  | none / str            | no       | `none`  | Human-readable description shown in the file panel.       |

`relationship` values (PDF/A-3 only):

- `"source"` — the PDF was created from this source file.
- `"data"` — the file was used to derive a visual presentation of the PDF.
- `"alternative"` — an alternative representation of the document.
- `"supplement"` — additional resources for the document.

## Recipes

### Attach a CSV with raw experimental data

```typst
#pdf.attach(
  "experiment.csv",
  relationship: "supplement",
  mime-type: "text/csv",
  description: "Raw oxygen readings from the Arctic experiment",
)
```

### Attach a hand-built bytes object (no on-disk file)

```typst
#let raw = bytes("col1,col2\n1,2\n3,4\n")
#pdf.attach(
  "inline.csv",
  data: raw,
  mime-type: "text/csv",
  description: "Inline-generated CSV",
)
```

### ZUGFeRD-style invoice (PDF/A-3 + machine-readable XML)

```typst
#pdf.attach(
  "factur-x.xml",
  data: read("factur-x.xml", encoding: none),
  relationship: "alternative",
  mime-type: "application/xml",
  description: "Factur-X structured invoice data",
)
```

(Requires `--pdf-standard a-3u` or higher.)

## When to use it

- Bundling **source** of a generated document (Typst, CSV, R script).
- Shipping **machine-readable structured data** beside the visual PDF.
- Including **standards-mandated** XML/JSON sidecars (invoices,
  reports).

For purely human-readable supplemental material, consider whether a
**page in the document** (or a downloadable URL via a link) is a
better fit — many PDF readers don't surface attachments prominently.
