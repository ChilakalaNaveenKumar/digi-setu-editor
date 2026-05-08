# `hide(body)` — invisible but layout-occupying content

Hides content while the layout still sees it. Useful for reserving exact-size space.

## Parameters

| Param  | Type    | Default  | Notes               |
| ------ | ------- | -------- | ------------------- |
| `body` | content  | required | Content to hide.    |

## Common patterns

| Goal                                            | Recipe                                    |
| ----------------------------------------------- | ----------------------------------------- |
| Reserve space matching some text                 | `#hide[Placeholder text]`                  |
| Pad a column to align numbers in a table        | `[#hide[12]4]` to align a 1-digit cell     |
| Spec out a layout before final content arrives  | Wrap todo content in `hide()`              |

## Accessibility & redaction

Hidden content is also **invisible to AT** — neither read nor referenced. Note however:

- Layout traces (the size & position) may still leak the **length / shape** of the hidden content.
- PDF artifacts may retain some metadata (bookmarks for hidden headings, etc.).
- **Do NOT use `hide` for security-sensitive redaction** — it's purely visual.

## Examples (compile-verified)

- `examples/12-hide/01-hide.typ` — reserve space the size of a word, alignment padding in a table, redaction caveat.

## Reference

https://typst.app/docs/reference/layout/hide/
