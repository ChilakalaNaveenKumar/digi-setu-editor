# `interpret-edge-args(args)` — sort positional arguments

`edge(...)` accepts an extremely flexible argument list. Vertices,
mark strings, labels, and other content can appear in any order. The
job of `interpret-edge-args` is to scan the positional arguments and
**bucket** them into the right slots.

## Resolution rules (from the manual)

`edge` walks `args.pos()` in order and assigns each item:

1. **Marks string** — `"->"`, `"->>"`, `"=>"`, `"hook'->"`, `"|->"`,
   `"<-"`, `"<->"`, etc. Goes into the `marks:` slot.
2. **Coordinate / node ref** — `(x, y)`, `<a>`, `(rel: …)`, etc.
   Appended to `vertices:`.
3. **Anything else** — a label (the first non-mark, non-coord
   content); ignored after the first to avoid silently misordering.

## Signature

```typst
interpret-edge-args(args, options) -> dict
```

The returned dict has keys `vertices`, `marks`, `label`, plus the rest
of the `edge` options (with defaults filled from `options`).

## Example

```typst
// Both calls are equivalent — interpret-edge-args sorts them out.
edge(<a>, <b>, "->", $f$)
edge(<a>, "->", <b>, $f$)
edge($f$, "->", <a>, <b>)
```

See [`examples/02-interpret-edge-args/02-interpret-edge-args.typ`](examples/02-interpret-edge-args/02-interpret-edge-args.typ).

## Pitfalls

- A *second* non-coord, non-mark item is silently dropped — combine
  multiple labels into one with `[A\\B]` or use the `label:` keyword.
- `marks:` and `label:` keyword arguments override anything `interpret-edge-args`
  finds positionally.

## Related

- [Tutorial: edges](../../../tutorial/04-edges.md)
- [`interpret-marks-arg`](01-interpret-marks-arg.md)
