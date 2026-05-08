# `terms` — term / definition list (glossary)

`terms(..children, tight: bool, separator: content, indent: length, hanging-indent: length = 2em, spacing: auto | length) -> content`

Renders pairs of terms and descriptions; multi-line descriptions get hanging indent so they group visually under the term.

## Markup shorthand

```
/ Ligature: A merged glyph.
/ Kerning: A spacing adjustment between two adjacent letters.
```

| Markup component | Role            |
| ---------------- | --------------- |
| `/ ` (slash + space) | Begins a term item |
| Text up to `:`    | The term         |
| Text after `:`    | The description  |

## Parameters

| Field            | Default                       | Notes                                                                            |
| ---------------- | ----------------------------- | -------------------------------------------------------------------------------- |
| `separator`      | `h(amount: 0.6em, weak: true)` | Between term and description. Pass `[ -- ]` etc. for visible separators.        |
| `indent`         | `0pt`                         | Whole-item left padding                                                           |
| `hanging-indent` | `2em`                         | Indent for continuation lines of the description (added on top of `indent`)       |
| `spacing`        | `auto`                        | Tight = `par.leading`, wide = `par.spacing`                                       |
| `tight`          | (markup-driven)               | Same blank-line rule as `list`/`enum`                                             |

### Visible separators with `h(...)`

The default separator is a *weak* horizontal space — it collapses around adjacent space. To insert a visible separator (em dash, colon, ratio symbol), pass content directly:

```typst
#set terms(separator: [ -- ])
```

To just widen the space, swap in a non-weak `h`:

```typst
#set terms(separator: h(2cm, weak: true))
```

## Programmatic construction

```typst
#terms(
  terms.item([Foo], [the description of foo]),
  terms.item([Bar], [the description of bar]),
)
```

For-loop bodies emit term items just like list/enum:

```typst
#for (k, v) in (a: 1, b: 2) [/ #k: value #v]
```

## Pitfalls

- **Term must be plain text up to the first `:`.** A `:` inside the term breaks parsing — wrap such terms in a function call: `#terms.item([key:value], [desc])`.
- **Default separator is weak space and may look invisible.** That's by design (the term and description sit in the same line). For glossary-style alignment, set an explicit separator and/or use a fixed `hanging-indent`.
- **`hanging-indent` is additive on top of `indent`.** Total left padding for continuation lines = `indent + hanging-indent`.
- **Tightness is markup-driven** (blank lines = wide). Use the function form to override.
- **Term content can have markup** (e.g. `/ *Bold term*: ...`), but no inline math `$...$` directly in the term — wrap in a function call.

## Examples (compile-verified)

- `examples/19-terms/01-terms-syntax-and-spacing.typ` — default markup, custom `separator`, `hanging-indent: 0pt`, `terms.item(...)` programmatic, for-loop emission.

## Reference

- Official: https://typst.app/docs/reference/model/terms/
- `list`: https://typst.app/docs/reference/model/list/
- `enum`: https://typst.app/docs/reference/model/enum/
