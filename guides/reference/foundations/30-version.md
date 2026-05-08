# `version` — multi-component version values

A `version` is a sequence of non-negative integer components. Comparison is **lexicographic** with implicit zero-padding for missing trailing components.

## Constructor

```typst
version()                  // empty (== 0 == 0.0 == 0.0.0 == ...)
version(1)                 // 1
version(1, 2, 3)           // 1.2.3
version(1, 2, 3, 4)        // 4+ components are allowed
version((1, 2, 3))         // single array argument is flattened
version((1, 2), 3)         // mixed: array spread + extra component → 1.2.3
```

The list of components is conceptually extended by an infinite stream of zeros, so `version(0, 8) == version(0, 8, 0)` and `version() == version(0)`.

## Field / index access

| Access        | Returns                                                          |
| ------------- | ---------------------------------------------------------------- |
| `v.major`     | first component                                                  |
| `v.minor`     | second component                                                 |
| `v.patch`     | third component                                                  |
| `v.at(i)`     | component at index `i`; returns `0` if `i` is past explicit length |
| `v.at(-1)`    | negative indexes count from the back of the **explicit** components |

Note: `.major` / `.minor` / `.patch` are the **only** named field accessors. Use `.at(idx)` for components beyond the third.

## Comparison

All standard comparison operators work component-wise (lexicographic):

```typst
#(version(1, 2)    < version(1, 2, 1))   // true (implicit 0 < 1)
#(version(1, 2)    == version(1, 2, 0))  // true (trailing zero implicit)
#(version(3, 2, 0) > version(4, 1, 0))   // false (3 < 4 at major)
```

The most common shape is **version-gated polyfill**:

```typst
#if sys.version >= version(0, 13, 0) [
  // new behavior
] else [
  // legacy behavior
]
```

## Conversion

| Operation      | Result                                                       |
| -------------- | ------------------------------------------------------------ |
| `str(v)`       | dotted form, e.g. `"0.14.2"`                                 |
| `array(v)`     | array of the **explicit** components as ints                 |
| `repr(v)`      | `version(0, 14, 2)`-style                                    |

## Pitfalls

- **No 4th-named field.** `v.build` does not exist; use `v.at(3)` for "extra" components.
- **`v.at(99)` returns 0**, doesn't error. Convenient most of the time, occasionally hides a bug — check `array(v).len()` if you need to know "how many components were explicitly given".
- **`.at(-1)` indexes the EXPLICIT length**, not the infinite virtual length. `version(1, 2).at(-1) == 2`, not `0`.
- **Pre-release / build metadata are not modeled.** Typst versions are pure integer tuples — there is no `1.0.0-beta.1` or `1.0.0+sha.abc` shape.
- **`sys.version` is the only version you compare to "the current Typst"**. Don't hardcode version numbers; let `sys.version` drive the branch.

## Examples (compile-verified)

- `examples/30-version/01-construct-and-fields.typ` — every constructor shape, named fields, `.at(idx)` (positive, past-end, negative), trailing-zero equivalence.
- `examples/30-version/02-comparison-and-sys.typ` — `sys.version` comparisons, ordering edge cases, `array(version)` conversion.

## Reference

- Official: https://typst.app/docs/reference/foundations/version/
- `sys.version`: https://typst.app/docs/reference/foundations/sys/
