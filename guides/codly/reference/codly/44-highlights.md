# `highlights`

Apply per-character highlights to specific positions inside a code line.
A list of dictionaries, each with the following keys:

| Key | Type | Notes |
| --- | ---- | ----- |
| `line` | int | the line number to highlight (one-indexed) |
| `start` | int | the character position to start highlighting; zero if omitted or `none` |
| `end` | int | the character position to end highlighting; end of line if omitted or `none` |
| `fill` | color | the fill of the highlight; defaults to [`highlighted-default-color`](./43-highlighted-default-color.md) |
| `tag` | content | optional tag displayed alongside the highlight |
| `inset` | length | overrides the global [`highlight-inset`](./48-highlight-inset.md) |
| `baseline` | length | overrides the baseline (defaults to the bottom component of `highlight-inset`) |
| `clip` | bool | overrides the global [`highlight-clip`](./50-highlight-clip.md) |
| `outset` | length | overrides the global [`highlight-outset`](./49-highlight-outset.md) |
| `radius` | length | overrides the global [`highlight-radius`](./45-highlight-radius.md) |
| `label` | label | only valid in `figure(kind: raw)`; sets the label by which the highlight can be referenced (`@<label>`) |

| Field | Value |
| ----- | ----- |
| Type | `array` or `none` |
| Default | `none` |
| Contextual function | yes |
| Automatically reset | no |
| Released in 1.3.1 | yes |

> **Info** — Line numbers are one-indexed; **character positions are
> zero-indexed**.

## Example

```typst
#codly(highlights: (
  (line: 4, start: 2, end: none, fill: red),
  (line: 5, start: 13, end: 19, fill: green, tag: "(a)"),
  (line: 5, start: 26, fill: blue, tag: "(b)"),
))
```py
def fib(n):
  if n <= 1:
    return n
  else:
    return fib(n - 1) + fib(n - 2)
print(fib(25))
```
```

### Local override of highlight parameters

```typst
#codly(highlights: (
  (line: 4, start: 2, end: none, fill: red),
  (line: 5, start: 13, end: 19, fill: green, tag: "(a)",
    inset: 0.1em, radius: 0.5em),
  (line: 5, start: 26, fill: blue, tag: "(b)", clip: false),
))
```

See [`examples/44-highlights/44-highlights.typ`](./examples/44-highlights/44-highlights.typ).

## Related

- [`43-highlighted-default-color.md`](./43-highlighted-default-color.md),
  [`45-highlight-radius.md`](./45-highlight-radius.md),
  [`46-highlight-fill.md`](./46-highlight-fill.md),
  [`47-highlight-stroke.md`](./47-highlight-stroke.md),
  [`48-highlight-inset.md`](./48-highlight-inset.md),
  [`49-highlight-outset.md`](./49-highlight-outset.md),
  [`50-highlight-clip.md`](./50-highlight-clip.md),
  [`51-reference-by.md`](./51-reference-by.md),
  [`../../tutorial/02-referencing.md`](../../tutorial/02-referencing.md).
