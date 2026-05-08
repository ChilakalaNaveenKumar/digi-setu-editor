# `mark()` — Standalone Arrowhead

Draws a single mark (arrowhead, dot, bracket, …) pointing toward a target.

## Signature

```text
mark(
  from: coordinate,
  to:   coordinate | angle,
  ..style: str | style,
)
```

## Parameters

- **`from`** — position to place the mark.
- **`to`** — coordinate the mark should point at, *or* an angle.
- **`..style`** — if the third positional is a `string`, it is treated as the
  mark name (e.g. `">"`, `">>"`, `"|"`) and overrides `mark.symbol` / `mark.end`.
  Otherwise these are key-value style overrides.

## Styling

- **Root:** `mark`
- See the full mark style dictionary in [`internals/mark/`](../internals/mark/).
  Common keys: `length`, `width`, `inset`, `sep`, `flip`, `reverse`,
  `harpoon`, `slant`, `scale`, `symbol`, `anchor`.

## Anchors

`tip`, `base`, `center`. The default is `tip`.

To centre the mark on `from` instead of having `from` be the tip, set
`anchor: "center"`.

## Pitfalls

- The third positional doubles as **either** mark name (string) **or** style
  key-value pairs. Mark names "win" over style keys.
- `mark` registers a separate path; if you want a marker on an existing line
  set its `mark:` style instead (e.g. `line(..., mark: (end: ">"))`).

## Example

See [`examples/05-mark/05-mark.typ`](./examples/05-mark/05-mark.typ).

## Related

- [`register-mark`](../styling/04-register-mark.md) — register a custom
  mark symbol you can then refer to by name
- [`mark.check-mark`](../internals/mark/01-check-mark.md) — validates the
  mark style dictionary
- [`mark.place-mark-on-path`](../internals/mark/03-place-mark-on-path.md)
  — places a mark on a single end of a path
- [`mark.place-marks-along-path`](../internals/mark/04-place-marks-along-path.md)
  — multi-mark placement (start, end, `pos:`)
