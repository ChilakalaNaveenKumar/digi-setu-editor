# `enum` — numbered list

`enum(..children, tight: bool, numbering: str | function = "1.", start: auto | int = auto, full: bool = false, reversed: bool = false, indent: length, body-indent: length, spacing: auto | length, number-align: alignment) -> content`

Vertical, consecutively numbered items. Markup shorthand:

| Markup            | Meaning                            |
| ----------------- | ---------------------------------- |
| `+ item`          | Auto-numbered item                 |
| `2. item`         | Explicitly start at `2`             |
| `5. item`         | Forces this item's number to `5`    |

Multi-paragraph item bodies work via indentation, same as `list`.

## Parameters

| Field          | Default          | Notes                                                                          |
| -------------- | ---------------- | ------------------------------------------------------------------------------ |
| `numbering`    | `"1."`           | Pattern (multi-symbol pattern enables nested numbering); OR a function         |
| `start`        | `auto`           | First number (default 1). Override per-item with explicit `N.` syntax           |
| `full`         | `false`          | If `true`, nested items show ALL ancestor numbers (e.g. `1.a)` on inner items) |
| `reversed`     | `false`          | Count downward                                                                  |
| `tight`        | (markup-driven)  | Same rules as `list` — blank lines = wide, adjacent = tight                    |
| `number-align` | `end + top`      | Numbers grow away from text by default; override e.g. `start + bottom`         |
| `body-indent`  | `0.5em`          | Gap between number and body                                                     |

### Multi-symbol numbering for nesting

`numbering: "1.a)"` puts `1)`, `2)`, `3)` at the top level and `a)`, `b)`, `c)` inside nested items. The `)` is the **suffix** (always appended); the `.` is a **prefix for the `a` symbol** and shows up only when the ancestor chain is shown — i.e. with `full: true` (see below), where you get `1.a)`, `1.b)` instead.

### Function numbering

```typst
#set enum(numbering: n => super[#n])  // raises numbers as superscript
```

If `full: false`, the function gets ONE number (the current item). If `full: true`, it gets the full ancestor chain.

## Programmatic items

```typst
#enum(
  enum.item(1)[First],
  enum.item(5)[Fifth],
)
```

`enum.item(number, body)` assigns explicit numbers. Auto-collected from for-loops emitting `+ ...`:

```typst
#for x in ("a", "b", "c") [+ #x]
```

## Pitfalls

- **Adjacent `+` and `-` items create separate lists/enums.** Don't mix in a single block.
- **`tight` is markup-driven** like `list`. Force wide via `#enum(...)` function form with `spacing:`.
- **`numbering:` pattern with too few symbols repeats the LAST symbol** for deeper levels — same rule as `numbering()`. `"1."` for 3 nested levels yields `1.2.3.`.
- **`reversed: true` reverses the labels but not the body order.** Items render in source order; only the numbers count down. To reverse content too, reverse the array before passing.
- **`start:` is per-enum, not per-document.** Sibling enums each restart unless you use `enum.item(N)` to set absolute numbers.

## Examples (compile-verified)

- `examples/05-enum/01-syntax-and-numbering.typ` — `+`, explicit `N.`, `numbering: "1.a)"`, function pattern, `start:`, `reversed:`.
- `examples/05-enum/02-full-and-item.typ` — `full: true` for nested ancestor numbering, `enum.item(N)[...]`, for-loop emission.

## Reference

- Official: https://typst.app/docs/reference/model/enum/
- `list`: https://typst.app/docs/reference/model/list/
- `numbering`: https://typst.app/docs/reference/model/numbering/
