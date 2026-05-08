# `none` — the absence of a value

The `none` type has exactly one value: `none`.

## Properties

- **Invisible in the document.** Inserting `#none` in markup produces *no* output, not even whitespace.
- **Empty code blocks evaluate to `none`.** `#({})` is `none`; `#({} == none)` is `true`.
- **`none` is the join identity.** `none + x == x` and `x + none == x` for any `x`. This makes it a clean "empty case" default in fold / join chains.
- **`none` is its own type.** It is distinct from `false`, from `0`, from the empty string, and from `auto`.

## When to use it

- As a **return value** for "no result" — `none` is the default return of any block whose last expression yields nothing.
- As a **parameter default** that means "skip / unset" — many built-in element parameters accept `none` to mean "do not emit this".
- As the **empty branch** in conditional content building, so the join still works:

```typst
#let maybe-section(title, body) = if body == none { none } else {
  [== #title] + parbreak() + body
}
```

## Pitfalls

- `none` is not `auto`. `auto` means "let the function pick a smart default"; `none` means "absent". Mixing them up will silently give the wrong layout in many built-in functions.
- `none == false` is `false`. Use explicit `== none` checks; don't lean on truthiness.
- A function whose last statement is an assignment or a `let` returns `none`. If you wanted content, make sure the last expression is content.

## Examples (compile-verified)

- `examples/18-none/01-none-and-join.typ` — invisibility, joins with int / str / content, empty-block equivalence, conditional section pattern.

## Reference

- Official: https://typst.app/docs/reference/foundations/none/
