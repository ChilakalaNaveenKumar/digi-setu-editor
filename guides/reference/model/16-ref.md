# `ref` — cross-references and citations

`ref(target: label, supplement: ?, form: "normal" | "page" = "normal") -> content`

Cross-references a labelled element OR cites a bibliography entry. Markup shorthand: `@target`, with optional override `@target[Custom]`.

## Two forms

| `form`     | What it produces                                       | Target requirement                                                                      |
| ---------- | ------------------------------------------------------ | --------------------------------------------------------------------------------------- |
| `"normal"` | Localized textual ref (e.g. `"Section 1"`, `"Figure 3"`) | Must be a **referenceable** element: `heading`, `figure`, `equation`, `footnote`, or a custom `figure` with `kind:` |
| `"page"`   | Page number where the label lives                       | Any label                                                                              |

The "supplement" word (Section, Figure, ...) follows the active `text(lang:)` setting and is automatically localized.

## Markup shorthand

```typst
@intro              // = #ref(<intro>)
@intro[Chapter]     // = #ref(<intro>, supplement: [Chapter])
```

## Customizing the supplement

`supplement:` accepts `none | auto | content | function`. Function form gets the referenced element and returns content:

```typst
#show ref.where(form: "normal"): set ref(supplement: it => {
  if it.func() == heading { "Chapter" } else { "Thing" }
})
```

## Show rules

`#show ref: it => ...` gives you full control. The handler's `it.element` may be `none` during early resolution passes — **always guard**:

```typst
#show ref: it => {
  let el = it.element
  if el == none or el.func() != math.equation { return it }
  // ... custom rendering ...
}
```

## `ref` vs `link`

| Use                              | Function           |
| -------------------------------- | ------------------ |
| Auto-numbered text + jump        | `ref` / `@`        |
| Page number jump                 | `ref(form: "page")`|
| Plain hyperlink, no auto-text    | `link`             |
| Bibliography citation            | `cite` / `@key`    |

`ref` and `cite` share the `@` syntax: if `key` is a bibliography entry, `@key` cites it; if it's a label, `@key` references it.

## Pitfalls

- **Label must be on a referenceable element.** A label inside a paragraph's body errors with `cannot reference text`. Put `<label>` after a heading/figure/equation, not inside a normal text block. (See the `label` page for the attaching-vs-inside distinction.)
- **`form: "page"` requires `set page(numbering: "...")`** in your document, otherwise the page has no number to reference.
- **`it.element == none` is normal**, not an error. Always handle it in show rules.
- **Custom kind figures need a custom supplement.** When you `figure(kind: "atom", supplement: [Atom], ...)`, references will use that supplement.
- **Default-form switch.** If a document only uses page references, set globally: `#set ref(form: "page")`.

## Examples (compile-verified)

- `examples/16-ref/01-ref-forms-and-supplement.typ` — `@`, `#ref(...)`, `[Custom]` supplement, `form: "page"`, equation reference.
- `examples/16-ref/02-show-rule-on-ref.typ` — `#show ref: ...` with `element == none` guard, equation-only override.

## Reference

- Official: https://typst.app/docs/reference/model/ref/
- `cite`: https://typst.app/docs/reference/model/cite/
- `link`: https://typst.app/docs/reference/model/link/
- `label`: https://typst.app/docs/reference/foundations/label/
