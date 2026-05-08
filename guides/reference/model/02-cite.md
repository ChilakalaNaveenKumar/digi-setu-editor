# `cite` — cite a work from the bibliography

`cite(key: label, supplement: none | content = none, form: none | "normal" | "prose" | "full" | "author" | "year" = "normal", style: auto | str | bytes = auto) -> content`

Adds a reference to a bibliography entry. **You must add a `#bibliography(...)` somewhere in the document** for citations to render.

## Syntax

The `@` shorthand (shared with `ref`) is the everyday form:

| Markup        | Equivalent                                       |
| ------------- | ------------------------------------------------ |
| `@arrgh`      | `#cite(<arrgh>)`                                 |
| `@arrgh[p. 7]`| `#cite(<arrgh>, supplement: [p. 7])`             |

Use `#cite(label("..."))` explicitly when the key has characters `@` can't parse (slashes, dots, etc.):

```typst
#cite(label("DBLP:books/lib/Knuth86a"))
```

## Forms

| `form`     | What it produces                                                                                  |
| ---------- | ------------------------------------------------------------------------------------------------- |
| `"normal"` | Default end-of-sentence citation in the active style                                              |
| `"prose"`  | In-sentence form, e.g. *"Smith (2024) argued..."*                                                  |
| `"full"`   | Mimics the full bibliography entry inline                                                         |
| `"author"` | Author(s) only                                                                                     |
| `"year"`   | Year only                                                                                          |
| `none`     | Silently registers the work (it appears in the bibliography listing) but renders nothing           |

`form: none` is useful for "include this in the bibliography but don't cite it inline".

## Supplement

`supplement:` adds page numbers, chapters, or other locator info. In the `@` shorthand, it goes in square brackets after the key:

```typst
This has been proven. @distress[p.~7]
```

## Per-citation style override

`style:` lets you force a single citation into a different bibliography style (string name, path to a CSL file, or raw bytes). Default `auto` uses the bibliography's style. Most documents leave this alone and configure the style on `#bibliography(..., style: "...")` instead.

## Pitfalls

- **Without a `#bibliography(...)` element, citations don't render.** You'll see Typst's "missing bibliography" error.
- **`@` and `cite` share the namespace with `ref`.** If a `<key>` exists as both a label and a bibliography key, behaviour is undefined — keep label names and citation keys distinct.
- **`prose` form is style-dependent.** Some styles render it like an in-text mention; others fall back to the parenthetical form. Check your output if you switch styles.
- **`form: none` still affects sorting** in styles that order entries by appearance — silent citations count as appearances.
- **`label("...")` accepts ANY non-empty string** including chars `@` rejects. Use it when the bibliography key has slashes / colons.

## Examples (compile-verified)

- `examples/02-cite/01-cite-syntax-and-form.typ` — `@key`, `#cite()` explicit, `form` variants, `supplement` via shorthand and explicit, `form: none` silent citation. Uses the shared `_assets/works.bib`.

## Reference

- Official: https://typst.app/docs/reference/model/cite/
- `bibliography`: https://typst.app/docs/reference/model/bibliography/
- `ref`: https://typst.app/docs/reference/model/ref/
- Style list: https://typst.app/docs/reference/model/cite/#parameters-style
