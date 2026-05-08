# `math.attach` / `math.scripts` / `math.limits` — sub/superscripts and limits

Three related functions for attaching things to a base. The everyday case uses **shorthand syntax** (`_` and `^`); reach for `attach()` when you need 4-corner attachments, and `scripts()`/`limits()` to override the smart positioning.

## Shorthand syntax

| Markup        | Effect                                |
| ------------- | ------------------------------------- |
| `x_i`          | Bottom (subscript / under)            |
| `x^2`          | Top (superscript / over)              |
| `x_i^2`        | Both                                  |
| `x_(i+1)`      | Group multiple tokens with `(...)`     |

## Smart positioning (`t:` and `b:`)

Typst auto-decides between **scripts** (sub/sup, beside the base) and **limits** (under/over, stacked) based on the base:

| Base                    | In inline equation | In block equation |
| ----------------------- | ------------------ | ----------------- |
| Plain variable `x`      | scripts            | scripts           |
| Big operator (`sum`, `product`, `integral`, `lim`, ...) | scripts | **limits**         |

Override per-call with `scripts(base)` or `limits(base)`. Override globally with `set math.op(limits: ...)` or a show rule:

```typst
#show math.equation.where(block: false): set math.op(limits: true)
```

## `math.attach(base, t: ?, b: ?, tl: ?, tr: ?, bl: ?, br: ?)`

| Slot | Default behaviour                                                                |
| ---- | -------------------------------------------------------------------------------- |
| `t`  | Top — smart positioning (script *or* over).                                       |
| `b`  | Bottom — smart positioning (script *or* under).                                   |
| `tl` | Top-left — always literal corner before base.                                     |
| `bl` | Bottom-left — always literal corner before base.                                  |
| `tr` | Top-right — always literal corner after base.                                    |
| `br` | Bottom-right — always literal corner after base.                                 |

Use `attach()` when shorthand isn't enough (e.g., tensor-style indices).

## `math.scripts(body)`

Force the base to display its `t:` / `b:` attachments as **scripts** (beside).

```typst
$ scripts(sum)_1^2 != sum_1^2 $
```

## `math.limits(body, inline: true)`

Force the base to display its `t:` / `b:` attachments as **limits** (above/below).

```typst
$ limits(A)_1^2 != A_1^2 $
```

`inline: false` only forces limits in *block* equations, not inline.

## Stretching the base under attachments

If you want the base itself to *stretch* to fit wide attachments (e.g. an arrow with text above), use [`stretch`](../math/15-stretch.md), not attach.

## Examples (compile-verified)

- `examples/02-attach/01-attach-shorthand.typ` — `_`/`^` shorthand, smart positioning, `scripts()`/`limits()` overrides, global show rule for inline operators.
- `examples/02-attach/02-four-corners.typ` — `attach()` with all six slots; tensor indices.

## Reference

https://typst.app/docs/reference/math/attach/
