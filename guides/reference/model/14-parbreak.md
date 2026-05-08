# `parbreak` — paragraph break

`parbreak() -> content`

Starts a new paragraph. **In markup, prefer a blank line.** You only need to call `parbreak()` explicitly inside *code* (loops, helpers) where blank lines aren't available.

## Markup form (idiomatic)

```typst
First paragraph.

Second paragraph.
```

## Code form (when blank lines aren't available)

```typst
#for i in range(3) {
  [Item #i: ]
  lorem(8)
  parbreak()
}
```

## Collapsing rule

Multiple consecutive paragraph breaks (whether blank lines or `parbreak()` calls) **collapse into a single break**. You can't "stack" parbreaks for extra space.

For controlled vertical space use `v(amount)`:

```typst
#v(2em)   // explicit vertical space
```

For a forced page break use `pagebreak()`. For a forced line break (within the same paragraph) use `linebreak()` or the `\` markup shorthand.

## Pitfalls

- **`parbreak()` ≠ `linebreak()`.** parbreak ends the paragraph and starts a new one (paragraph-level styling re-applies). linebreak just wraps within the current paragraph.
- **Spamming `parbreak()` does nothing.** It's collapsed. Use `v(...)` for spacing.
- **Inside a list/table cell**, parbreak makes a new paragraph *inside* that cell — it does not exit the cell or list item.

## Examples (compile-verified)

- `examples/14-parbreak/01-parbreak.typ` — markup blank-line form, `parbreak()` inside a `for` loop, collapsing rule, `v(...)` for actual spacing.

## Reference

- Official: https://typst.app/docs/reference/model/parbreak/
- `pagebreak`: https://typst.app/docs/reference/layout/pagebreak/
- `linebreak`: https://typst.app/docs/reference/text/linebreak/
- `v` (vertical space): https://typst.app/docs/reference/layout/v/
