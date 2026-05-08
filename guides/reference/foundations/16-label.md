# `label` — references and styling targets

A label is a marker attached to an element. Labels are how you make elements **referenceable** (`#ref`, `@name`), **queryable** (`#query`), and **show-rule-targetable** (`show <name>: ...`).

## Two ways to create a label

| Form               | Allowed name characters                       | When to use                              |
| ------------------ | --------------------------------------------- | ---------------------------------------- |
| `<name>`           | letters, digits, `_`, `-`, `:`, `.` (non-empty) | almost always                            |
| `label("string")`  | **any** non-empty string                      | dynamic names, special chars, code mode  |

`#str(some-label)` returns the label's name as a string.

## Attachment rule

A label attaches to **the closest preceding element that is not a space, in the same scope**.

This makes the placement matter:

```typst
= Heading <a>             // <a> is a sibling AFTER the heading
                          // -> attaches to the heading element
                          // == #heading[Heading] <a>

= Heading #label("b")     // #label("b") is INSIDE the heading body
                          // -> attaches to the body's text/content
                          // == #heading[Heading #label("b")]
```

Both labels exist in the document, but they target *different things*. A `#ref` to the second one fails with `error: cannot reference text` because text isn't a referenceable element.

> **Rule of thumb**: to make an element referenceable, place the label **after** the element using the `<name>` form.

## Show rules on labels

```typst
#show <important>: set text(fill: red)
#show label("dyn-name"): emph
```

The two forms are equivalent; `label("...")` lets you target names that the bracket syntax can't represent.

## Pitfalls

- `Hello #[<label>]` does **not** label "Hello" — the label is inside the content block, so it's in a different scope.
- Labels can only be attached in **markup** mode. In code mode, construct via `label("name")` and place the result in markup.
- A label on a heading body (`= H #label("x")`) is a common gotcha — `@x` will fail. Use `= H <x>` instead.

## Examples (compile-verified)

- `examples/16-label/01-syntax-and-show.typ` — `<a>` and `label("b.special:1")` syntax; show rules on both forms.
- `examples/16-label/02-attaching-vs-inside.typ` — the heading-vs-body attachment difference, with the failing case explained in prose.

## Reference

- Official: https://typst.app/docs/reference/foundations/label/
