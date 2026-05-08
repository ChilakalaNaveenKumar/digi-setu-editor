# `is-space(el)` — content whitespace test

Return `true` iff `el` is whitespace content — a space, sequence of
spaces, or a `linebreak()`.

## Signature

```typst
is-space(el: content) -> bool
```

## Why Fletcher needs it

The mark-shorthand parser walks an array of `content` items. When it
sees a string, it tries to parse marks; when it sees content like
`$f$`, that's a label; **anything that's whitespace is skipped**.
That skip is `is-space`.

The same logic applies to `interpret-edge-args` — leading/trailing
whitespace must be stripped or it would be misclassified as a label.

## Example

```typst
#let s = [ ]
#fletcher.is-space(s)             // → true
#fletcher.is-space([ \  ])        // → true
#fletcher.is-space([hello])       // → false
```

See [`examples/04-is-space/04-is-space.typ`](examples/04-is-space/04-is-space.typ).

## Pitfalls

- `is-space` returns `false` for non-content like strings or numbers
  — guard your input or coerce with `[…]`.
- A *math* space (e.g. `$ thin space $`) is NOT regular whitespace
  content; the helper returns `false`.

## Related

- Used by [`interpret-marks-arg`](../edge/01-interpret-marks-arg.md)
  and [`interpret-edge-args`](../edge/02-interpret-edge-args.md).
