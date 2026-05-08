# `interpret-marks-arg(arg)` — normalise the `marks:` argument

Translate the many forms accepted by `edge(marks: …)` into a canonical
list of mark dicts.

## Accepted inputs

| Form | Meaning |
| ---- | ------- |
| `none` | No marks. |
| `"->"`, `"=>"`, `">->"`, `"hook'->>"`, `"\|->"` … | Mark shorthand string. Parsed character-by-character. |
| `(none, ">", none)` | Same as a shorthand, expressed as a list of mark slots. |
| `(<dict>, <dict>)` | Pre-built mark dicts (use [`MARKS.get()`](../../../tutorial/06-custom-marks.md) and the constructors). |

## Signature

```typst
interpret-marks-arg(arg) -> array
```

The output is always an array of `(mark-dict, mark-dict, …)` ready to
hand to [`draw-mark`](../marks/03-draw-mark.md).

## Example

```typst
#diagram(
  node((0, 0), [A]),
  node((1, 0), [B]),
  edge((0, 0), (1, 0), "hook'->>"),
)
```

The shorthand `"hook'->>"` is parsed by `interpret-marks-arg` into a
list of (left hook, line, right double-headed arrow) marks.

See [`examples/01-interpret-marks-arg/01-interpret-marks-arg.typ`](examples/01-interpret-marks-arg/01-interpret-marks-arg.typ).

## Pitfalls

- Unknown shorthand characters are silently skipped — typos will
  produce *fewer* marks rather than an error.
- The double-quoted apostrophe form (`"hook'->>"`) flips the cap
  direction; it's a property of the prefix mark, not a separator.

## Related

- [Tutorial: marks and arrows](../../../tutorial/05-marks-and-arrows.md)
- [`MARKS`](../marks/00-marks-overview.md) registry of standard marks.
