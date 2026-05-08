# `resolve-mark(mark, defaults)` — finalise a mark dictionary

Resolves a mark by:

1. Following any `inherit:` chain through `fletcher.MARKS`.
2. Filling in default values for missing keys.
3. Evaluating any closure values (`field: mark => ...`) by passing
   the partially-resolved mark.

## Signature

```typst
resolve-mark(mark: dict, defaults: dict = (..)) -> dict
```

## Example

```typst
#context fletcher.resolve-mark((
  a: 1,
  b: 2,
  c: mark => mark.a + mark.b,
))
```

Result:

```typst
(
  a: 1,
  b: 2,
  c: 3,
  rev: false,
  flip: false,
  scale: 100%,
  extrude: (0,),
  tip-end: 0,
  tail-end: 0,
  tip-origin: 0,
  tail-origin: 0,
)
```

See [`examples/02-resolve-mark/02-resolve-mark.typ`](examples/02-resolve-mark/02-resolve-mark.typ).

## Pitfalls

- A closure that references a key not yet resolved silently returns
  `none`. Order your closures so dependencies appear first.
- The `defaults` argument may add extra entries — handy for
  resolving marks against a custom default schema.
- `resolve-mark` doesn't draw anything; it only normalises the
  dictionary. Pass the result to [`draw-mark`](03-draw-mark.md).

## Related

- Drawing: [`03-draw-mark.md`](03-draw-mark.md)
- Anatomy: [`04-mark-debug.md`](04-mark-debug.md)
