# `list` — bullet list

`list(..children: content, tight: bool, marker: content | array | function, indent: length, body-indent: length, spacing: auto | length) -> content`

Renders items vertically, each introduced by a marker. Markup shorthand: `- item` per line. Indented content under an item belongs to it.

```typst
- one
- two
  - nested
- three
```

## Parameters

| Field         | Default               | Notes                                                                                       |
| ------------- | --------------------- | ------------------------------------------------------------------------------------------- |
| `marker`      | `([•], [‣], [–])`     | Single content / array (cycles per depth) / function `depth -> content`                     |
| `tight`       | (markup-driven)       | Auto-set by markup based on blank lines; **not overridable** via set rule from markup       |
| `indent`      | `0pt`                 | Per-item indent (left padding of the whole item)                                            |
| `body-indent` | `0.5em`               | Gap between marker and body                                                                 |
| `spacing`     | `auto`                | `auto` = `par.leading` (tight) or `par.spacing` (wide)                                      |

## Tight vs wide

| Markup pattern              | Tightness | Spacing source     |
| --------------------------- | --------- | ------------------ |
| Items adjacent (no blank line) | tight   | `par.leading`      |
| Blank lines between items   | wide      | `par.spacing`      |

You **cannot** override markup-set tightness via `set list(tight: ...)` — the markup form wins. To force wide on a programmatic list, use the function form (`#list(...)`) with explicit `spacing:`.

## Programmatic construction

```typst
#list(list.item[a], list.item[b])

#for x in ("A", "B", "C") [
  - Item #x
]
```

Loops emit list items that get auto-collected into a list.

## Pitfalls

- **Trailing space matters.** `- foo` (with space) is a list item. `-foo` (no space) is literal text starting with `-`.
- **Nesting via indentation**, not via additional dashes. Use 2 spaces (or any consistent amount) before the inner `-`.
- **Markup `tight` cannot be unset.** If you need wide spacing on a programmatic list, build it with `#list(...)` directly, not the markup syntax.
- **Marker arrays cycle**, they don't truncate. A 3-element marker array repeats from index 0 at depth 3.
- **Mixing `+` and `-` items at the same indent** creates two separate lists (a list and an enum).

## Examples (compile-verified)

- `examples/10-list/01-syntax-and-marker.typ` — markup with nesting, single custom marker, cycling array marker, function-form marker.
- `examples/10-list/02-tight-vs-wide.typ` — tight vs wide via blank lines, for-loop emission, programmatic `#list(list.item[...])`.

## Reference

- Official: https://typst.app/docs/reference/model/list/
- `enum` (numbered list): https://typst.app/docs/reference/model/enum/
- `terms` (term/definition list): https://typst.app/docs/reference/model/terms/
