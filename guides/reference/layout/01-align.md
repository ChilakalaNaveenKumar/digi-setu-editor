# `align(alignment, body)` — align content horizontally and vertically

Aligns a piece of content within its container.

## Parameters

| Param      | Type       | Default       | Notes                                            |
| ---------- | ---------- | ------------- | ------------------------------------------------ |
| `alignment` | alignment | `start + top`  | One- or two-axis alignment.                       |
| `body`     | content    | required       | The content to align.                              |

## Two-axis alignment

Combine a horizontal and a vertical alignment with `+`:

| Combination          | Meaning                |
| -------------------- | ---------------------- |
| `center + horizon`    | Dead center            |
| `right + bottom`      | Bottom-right corner     |
| `start + top`         | Default (top-start)     |

## Logical vs absolute

| Alignment      | Behaviour                                      |
| -------------- | ---------------------------------------------- |
| `left`/`right` | Always absolute LTR                              |
| `start`/`end`  | Follows the text direction (LTR or RTL)         |

For multi-language documents prefer `start`/`end` so layouts mirror correctly in RTL.

## `align` is block-level

`align()` interrupts the current paragraph — it forces its content into its own block. To align pieces **within the same line**, use [fractional spacing](./11-h.md) instead:

```typst
Start #h(1fr) End          // aligns "End" to the right of the same line
```

## Set rule vs function form

```typst
#set align(center)              // applies to following content
#align(right)[just this bit]    // one-shot
```

## Nesting

You can nest `align` calls or set-rules to vary alignment in a sub-region:

```typst
#align(center, block[
  #set align(left)
  This block is centered as a whole, but its inner text is left-aligned.
])
```

## Examples (compile-verified)

- `examples/01-align/01-align.typ` — horizontal centering, two-axis alignment, logical start/end with RTL flip, same-line `h(1fr)` pattern.

## Reference

https://typst.app/docs/reference/layout/align/
