# `pdf.artifact` – Mark Content as Decorative

```typst
pdf.artifact(kind: "other" | "header" | "footer" | "page", body) -> content
```

Marks `body` as a **PDF artifact** — content that is *not* meant to
be read by Assistive Technology (AT). Artifacts are skipped by screen
readers, hidden during reflow, and excluded from text extraction.

Typical artifacts:

- Purely decorative images that don't add meaning.
- Watermarks.
- Repeated content like page numbers, ornaments, marker lines.
- Cut marks or color bars on the physical page.

## What's already auto-tagged

Typst marks these as artifacts automatically — you don't need to
wrap them yourself:

- Page headers and footers (the content of `header:` / `footer:`).
- Page backgrounds and foregrounds (`background:` / `foreground:`).
- Repeated table headers and footers (the *repetitions*; the
  original is still semantic).
- Hyphens inserted by automatic hyphenation.
- Shapes and paths (`circle`, `square`, `polygon`, `curve`, `line`,
  `rect`, `ellipse`) — but their content remains semantic.

Use `pdf.artifact` for everything else.

## Parameters

| Name   | Type      | Required | Default   | Notes                                |
| ------ | --------- | -------- | --------- | ------------------------------------ |
| `kind` | string    | no       | `"other"` | Artifact category (see below).       |
| `body` | content   | yes      | —         | Content to mark as the artifact.     |

`kind` values:

- `"header"` — repeats at the top of each page.
- `"footer"` — repeats at the bottom of each page.
- `"page"` — physical-page artifact (cut marks, color bars).
- `"other"` — everything else (watermarks, decoration, repeated
  content). This is the default.

## Important behavior

- **One-way.** Once content is inside an artifact, you *cannot* make
  any of it semantic again. Split semantic and decorative parts
  *before* wrapping.
- **Apply minimally.** Wrap only the decorative bit. Marking a whole
  region artifact-style hides everything inside from AT.
- The `pdf.` prefix may go away in the future — this function may
  move so that it can also hide content in HTML export.

## Recipes

### Decorative watermark

```typst
#set page(background: pdf.artifact[
  #place(center + horizon, rotate(-30deg, text(60pt, gray.lighten(70%))[DRAFT]))
])
```

(`set page(background: ...)` already auto-tags its argument as an
artifact, but being explicit doesn't hurt and documents intent.)

### Decorative ornament between sections

```typst
== Conclusion

#pdf.artifact[
  #align(center, text(20pt, gray)[*]
)]
```

### Cut marks on a print-ready page

```typst
#set page(foreground: pdf.artifact(kind: "page")[
  #place(top + left, dx: 5mm, dy: 5mm, line(length: 8mm))
  #place(top + right, dx: -5mm, dy: 5mm, line(length: 8mm))
])
```

## When in doubt

Ask: *would it be annoying if a screen reader announced this?* If
yes, it's probably an artifact. If it could be useful for an AT user
to know about it, it's not — describe it in alt text or surrounding
prose instead.
