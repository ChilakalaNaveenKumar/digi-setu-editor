# `bibliography` — reference listing

`bibliography(sources: str | bytes | array, title: none | auto | content = auto, full: bool = false, style: str | bytes = "ieee") -> content`

Loads a bibliography file and renders the listing of cited works (or all works, with `full: true`).

## File formats

| Format       | Extension      | Notes                                              |
| ------------ | -------------- | -------------------------------------------------- |
| Hayagriva    | `.yaml`/`.yml` | Native Typst format (richer metadata)               |
| BibLaTeX     | `.bib`         | Standard LaTeX bibliography format                  |

`sources` accepts a single path string, raw bytes, or an array combining several files.

```typst
#bibliography("works.bib")
#bibliography(("a.bib", "b.bib"), style: "apa")
```

## Parameters

| Field    | Default     | Notes                                                                            |
| -------- | ----------- | -------------------------------------------------------------------------------- |
| `title`  | `auto`      | `auto` = localized (e.g. "Bibliography" / "References"). `none` = no heading. Pass content for a custom heading. |
| `full`   | `false`     | `true` shows ALL entries from the file, even uncited ones                        |
| `style`  | `"ieee"`    | Built-in style name, path to a CSL file, or raw CSL bytes                        |

To **number** the bibliography heading: `#show bibliography: set heading(numbering: "1.")`.

## Style picks per discipline

| Discipline                  | Typical style                                          |
| --------------------------- | ------------------------------------------------------ |
| Engineering, IT             | `"ieee"`                                               |
| Psychology, Life Sciences   | `"apa"`                                                |
| Social sciences             | `"chicago-author-date"`                                |
| Humanities                  | `"mla"`, `"chicago-notes"`, `"harvard-cite-them-right"` |
| Economics                   | `"harvard-cite-them-right"`                            |
| Physics                     | `"american-physics-society"`                           |

The full list of built-in style strings (90+) is on the official page. You can also drop in a custom CSL file by passing its path string.

## Layout

The element renders as:

1. A heading (controlled by `title`).
2. The list of cited entries, formatted by `style`.

Position the bibliography wherever you want it in the document — typically at the end:

```typst
= References
#bibliography("works.bib", title: none)
```

## Pitfalls

- **Path is resolved per Typst's path rules** — see the Syntax → Paths section. Relative paths are relative to the current `.typ` file, not the working directory.
- **A document may have at most one `bibliography` element** in practice (multiple cause overlapping listings). Combine multiple `.bib` files via the `sources` array instead.
- **`full: true` includes ALL entries** — useful for "complete reading list" appendices, noisy for a normal paper. Combine with `cite(form: none)` if you want to silently include just a few extras.
- **Switching styles changes both the inline citation form AND the listing.** If you've configured per-citation `style:` overrides, keep them in mind.
- **Hayagriva vs BibLaTeX.** Both work, but Hayagriva supports more fields (online resources, parent works) and integrates more cleanly with Typst's localization. Prefer it for new projects.

## Examples (compile-verified)

- `examples/01-bibliography/01-basic-bibliography.typ` — IEEE style, custom `title:`, mixing `@key` citations and `cite(form: none)` for silent registration.
- `examples/01-bibliography/02-styles-and-full.typ` — APA style, `full: true` to list uncited entries, `title: none` to suppress the heading.

## Reference

- Official: https://typst.app/docs/reference/model/bibliography/
- `cite`: https://typst.app/docs/reference/model/cite/
- `ref`: https://typst.app/docs/reference/model/ref/
- Hayagriva file format: https://github.com/typst/hayagriva/blob/main/docs/file-format.md
- CSL spec: https://citationstyles.org/
