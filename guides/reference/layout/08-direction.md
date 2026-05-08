# `direction` (type) — flow direction

The four directions content can be laid out along.

## Values

| Value  | Direction        |
| ------ | ---------------- |
| `ltr`   | Left to right    |
| `rtl`   | Right to left    |
| `ttb`   | Top to bottom    |
| `btt`   | Bottom to top    |

These names are available globally and inside `direction.<name>`.

## Methods

| Method     | Returns                                                |
| ---------- | ------------------------------------------------------ |
| `axis()`    | `"horizontal"` or `"vertical"`                          |
| `sign()`    | `+1` or `-1` for use in calculations                   |
| `start()`   | The starting alignment (`ltr.start() == left`)          |
| `end()`     | The ending alignment (`ltr.end() == right`)             |
| `inv()`     | The inverse direction                                   |

## Static constructors

| Call                  | Returns                                |
| --------------------- | -------------------------------------- |
| `direction.from(side)` | The direction *starting* from `side` (`from(left) == ltr`) |
| `direction.to(side)`   | The direction *ending* at `side` (`to(top) == btt`)  |

## Used in

- `stack(dir: ...)`
- `text(dir: ...)`
- `page(direction: ...)`
- `grid(rows-direction: ...)` (where applicable)

## Examples (compile-verified)

- `examples/08-direction/01-direction.typ` — `stack` with each of the four dirs, all helper methods, `from`/`to` constructors.

## Reference

https://typst.app/docs/reference/layout/direction/
