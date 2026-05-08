# `ratio` (type) — percentage

A ratio is written as a number followed by `%`. Ratios most often appear inside [`relative`](./22-relative.md) lengths, but they can also describe any other property whose value is "a fraction of some base" (scaling factor, delimiter height, etc.).

## Notation

```typst
25%             // a ratio
25% + 1cm       // a relative (ratio + length)
```

## Multiplication table

| Multiply by                        | Example          | Result    |
| ---------------------------------- | ---------------- | --------- |
| ratio                               | `27% * 10%`        | `2.7%`     |
| [length](./14-length.md)            | `27% * 100pt`      | `27pt`     |
| relative                            | `27% * (10% + 100pt)` | `2.7% + 27pt` |
| [angle](./03-angle.md)              | `27% * 100deg`     | `27deg`    |
| `int`                               | `27% * 2`          | `54%`      |
| `float`                             | `27% * 0.37037`    | `10%`      |
| [fraction](./09-fraction.md) (`fr`) | `27% * 3fr`        | `0.81fr`   |

## Display rounding

When a ratio is displayed via `repr()` it's rounded to **two significant digits** for readability.

## Where it shows up

- Lengths: `width: 50%`, `inset: 5%`
- Scaling: `scale(x: 75%)`, `scale(75%)`
- Math delimiter sizes: `lr(|...|, size: 150%)`
- `cancel(length: 200%)` — line length relative to the diagonal
- `image(width: 60%)` — width relative to container

## Examples (compile-verified)

- `examples/21-ratio/01-ratio.typ` — ratio as length component, multiplication with all 7 supported types, scale + delim-size as non-length uses.

## Reference

https://typst.app/docs/reference/layout/ratio/
