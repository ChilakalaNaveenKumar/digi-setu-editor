# `skew(ax: 0deg, ay: 0deg, origin: center + horizon, reflow: false, body)` — skew content

Skews content along the horizontal and/or vertical axis. Like `rotate`/`scale`, layout is unaffected unless `reflow: true`.

## Parameters

| Param    | Type      | Default              | Notes                                                                |
| -------- | --------- | -------------------- | -------------------------------------------------------------------- |
| `ax`      | angle     | `0deg`                | Horizontal skewing angle.                                            |
| `ay`      | angle     | `0deg`                | Vertical skewing angle.                                              |
| `origin`  | alignment  | `center + horizon`    | Pivot — stays fixed during the operation.                            |
| `reflow`  | bool      | `false`               | Adjust layout to skewed bounding box.                                 |
| `body`    | content    | required              | Content to skew.                                                      |

## Common pattern: fake italic

```typst
#skew(ax: -12deg)[
  Fake italic for fonts that don't ship a real italic.
]
```

## Per-axis behavior

| Form                  | Effect                                       |
| --------------------- | -------------------------------------------- |
| `skew(ax: 30deg)[X]`   | Horizontal slant (right-leaning).            |
| `skew(ay: 30deg)[X]`   | Vertical slant.                              |
| `skew(ax: 10deg, ay: -10deg)` | Combined (parallelogram-like).         |

## Examples (compile-verified)

- `examples/26-skew/01-skew.typ` — fake italic, horizontal/vertical/combined skew, origin alignment, `reflow: true`.

## Reference

https://typst.app/docs/reference/layout/skew/
