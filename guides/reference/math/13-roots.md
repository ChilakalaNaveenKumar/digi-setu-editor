# `math.sqrt` / `math.root` — square and indexed roots

## `math.sqrt(radicand)`

Renders a plain square root. The radical sign auto-stretches over the radicand.

| Param      | Type    | Default  | Notes                          |
| ---------- | ------- | -------- | ------------------------------ |
| `radicand` | content | required | The expression under the root. |

## `math.root(index, radicand)`

Renders a general root with an explicit index.

| Param      | Type             | Default  | Notes                                          |
| ---------- | ---------------- | -------- | ---------------------------------------------- |
| `index`    | `none` / content | `none`    | Root index. `none` ≡ `sqrt`.                  |
| `radicand` | content           | required | The expression under the root.                 |

```typst
$ root(3, x) $          // ∛x
$ root(n, x) $          // ⁿ√x
$ root(none, x) $       // same as sqrt(x)
```

## Examples (compile-verified)

- `examples/13-roots/01-roots.typ` — `sqrt`, indexed `root`, nested roots, quadratic formula.

## Reference

https://typst.app/docs/reference/math/roots/
