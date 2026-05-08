# `emph` — italic emphasis (toggling)

`emph(body) -> content`

Toggles italic style:

| Current text style | Result    |
| ------------------ | --------- |
| `"normal"`         | `"italic"` |
| `"italic"`         | `"normal"` |
| `"oblique"`        | `"normal"` |

This **toggle** behavior matters: nesting `emph[emph[x]]` makes the inner `x` revert to upright — the same UX as Word's italic button, not a guarantee that "this is italic".

## Markup shorthand

Wrap content in underscores: `_text_`. The shorthand only fires at **word boundaries**. To italicize part of a word, call the function:

```typst
extra#emph[ordin]ary   // works
extra_ordin_ary         // doesn't italicize -- underscores stay literal
```

## Show rules

`#show emph: ...` matches every `emph` element. The handler receives an `emph` element whose `.body` is the inner content:

```typst
#show emph: it => text(fill: blue, it.body)
```

Use the function form (`emph[...]`) inside complex content to make selectors and show rules unambiguous.

## Pitfalls

- **Toggle, not assignment.** A `set text(style: "italic")` *forces* italic; `emph` *flips*. Reach for `text(style: "italic", ...)` when you mean "this MUST be italic regardless of context".
- **Word-boundary shorthand** can silently fail. If `_inside_word_` doesn't render italic, switch to `#emph[...]`.
- **Italic vs oblique** depends on the font. Some fonts have a true italic; others fake it with oblique. The toggle treats both as "active".

## Examples (compile-verified)

- `examples/04-emph/01-emph-syntax-and-show.typ` — `_..._` shorthand, `#emph[...]` function, partial-word case, show rule, nested-toggle behavior.

## Reference

- Official: https://typst.app/docs/reference/model/emph/
- `text` element (for forced styles): https://typst.app/docs/reference/text/text/
