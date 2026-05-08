# `annotations`

The annotations to display on the right side of the code block. A list
of annotations that are automatically numbered (formatter controlled by
[`annotation-format`](./41-annotation-format.md)).

Each entry is a dictionary:

| Key | Type | Notes |
| --- | ---- | ----- |
| `start` | int | the line number to start the annotation (one-indexed) |
| `end` | int | the line number to end the annotation. If missing or `none`, the annotation contains only `start`. |
| `content` | content / showable | the annotation body. If missing or `none`, only the number is shown. Generally wrap in `rotate(90deg)`. |
| `label` | label | only valid when the code block is in a `figure(kind: raw)`; sets the label by which the annotation can be referenced (`@<label>`). |

| Field | Value |
| ----- | ----- |
| Type | `array` or `none` |
| Default | `none` |
| Contextual function | yes |
| Automatically reset | yes |
| Released in 1.3.1 | yes |

> **Info** — Line numbers are one-indexed.
>
> **Experimental** — Report issues at https://github.com/Dherse/codly.

## Known issues

- Annotations cannot overlap.
- Annotations that span a page break will not work correctly.
- Annotations on the first line of a code block will not work correctly.
- Annotations that span lines that overflow (one line of code wrapping
  to two lines of text) will not work correctly.

## Example

```typst
#codly(
  annotations: (
    (
      start: 2, end: 5,
      content: block(
        width: 2em,
        rotate(-90deg, reflow: true,
          align(center)[Function body])
      ),
    ),
  ),
)
```py
def fib(n):
  if n <= 1:
    return n
  else:
    return fib(n - 1) + fib(n - 2)
fib(25)
```
```

See [`examples/40-annotations/40-annotations.typ`](./examples/40-annotations/40-annotations.typ).

## Related

- [`41-annotation-format.md`](./41-annotation-format.md),
  [`51-reference-by.md`](./51-reference-by.md),
  [`../../tutorial/02-referencing.md`](../../tutorial/02-referencing.md).
