# `array` — Sequences of Values

`array` is Typst's ordered sequence container. Items can be of mixed
types. The literal syntax is parentheses with comma-separated values:

```typst
#let xs = (1, "two", 3.0, true)
#()             // empty
#(42,)          // ONE-element array — trailing comma is REQUIRED
#(1 + 2) * 3    // NOT an array — this is parenthesized arithmetic
```

> **Single-element gotcha.** `(42)` parses as the number `42` in
> parentheses, not as a one-element array. Always write `(42,)`.

## Indexing

Zero-based, with negative indices wrapping from the end. Mutating an
element uses assignment to `at()`:

```typst
#let xs = (1, 7, 4, -3, 2)
#xs.at(0)            // 1
#xs.at(-1)           // 2
#(xs.at(0) = 99)     // mutate
```

`at(i, default: ...)` returns the default instead of erroring on
out-of-range indices.

## Membership and search

| Method | Returns |
| ------ | ------- |
| `xs.contains(v)` | `bool` — same as `v in xs` |
| `xs.find(fn)` | first item where `fn(item) == true`, or `none` |
| `xs.position(fn)` | index of first match, or `none` |

```typst
#3 in (1, 2, 3)              // true
#xs.find(calc.even)          // first even number
#xs.position(x => x < 0)     // index of first negative
```

## Adding, removing, reordering

| Method | Effect |
| ------ | ------ |
| `xs.push(v)` | append in place |
| `xs.pop()` | remove and return the last item |
| `xs.insert(i, v)` | insert at index `i` (mutates) |
| `xs.remove(i)` / `xs.remove(i, default: ...)` | delete at `i`, return it |
| `xs.rev()` | new reversed array |
| `xs.sorted(key: ..., by: ...)` | new stable-sorted array |
| `xs.dedup(key: ...)` | new array, only first of each unique key |

`sorted` accepts a `key` function (project to comparable values) and/or
a `by` function (custom comparator returning `true` if the first arg
should come first). For multi-criteria sorts, return a tuple from `key`
— Typst compares lexicographically.

```typst
#((a: 2), (a: 1), (a: 3)).sorted(key: it => it.a)
#("ant", "bee", "cat", "dog").sorted(
  key: w => w.len(), by: (l, r) => l >= r,    // descending
)
```

## Slicing and chunking

| Method | What |
| ------ | ---- |
| `xs.slice(start)` / `slice(start, end)` / `slice(start, count: n)` | sub-array |
| `xs.chunks(n)` / `chunks(n, exact: true)` | non-overlapping windows of size `n` (drop remainder if `exact`) |
| `xs.windows(n)` | sliding windows of size `n` |
| `xs.split(value)` | split at every occurrence of `value` |

```typst
#(1, 2, 3, 4, 5).chunks(2)             // ((1,2), (3,4), (5,))
#(1, 2, 3, 4, 5).windows(3)            // ((1,2,3), (2,3,4), (3,4,5))
#(1, 1, 2, 3, 2, 4).split(2)           // ((1,1), (3,), (4,))
```

## Map / filter / fold (the functional core)

| Method | Notes |
| ------ | ----- |
| `xs.map(fn)` | apply `fn` to every item |
| `xs.filter(fn)` | keep items where `fn(item) == true` |
| `xs.fold(init, (acc, x) => ...)` | reduce with explicit initial value |
| `xs.reduce((acc, x) => ...)` | like `fold`, seeded with `xs.first()`; returns `none` on empty |
| `xs.sum(default: ...)` / `xs.product(default: ...)` | works on any addable/multiplicable type |
| `xs.any(fn)` / `xs.all(fn)` | logical predicates |

```typst
#(1, 2, 3, 4).map(x => x * x)          // (1, 4, 9, 16)
#(1, 2, 3, 4).filter(calc.even)        // (2, 4)
#(1, 2, 3, 4).fold(0, (a, b) => a + b) // 10
#(2, 1, 4, 3).reduce((acc, x) => calc.max(acc, x))  // 4
```

## Joining and interleaving

| Method | Notes |
| ------ | ----- |
| `xs.join(sep, last: ..., default: ...)` | combine into one value with `sep` between, optional different separator before the last item |
| `xs.intersperse(sep)` | new array with `sep` between every pair |
| `xs.flatten()` | recursively flatten nested arrays |

```typst
#("Alice", "Bob", "Charlie").join(", ", last: ", and ")
#("A", "B", "C").intersperse("-")      // ("A", "-", "B", "-", "C")
#(1, (2, (3, 4))).flatten()            // (1, 2, 3, 4)
```

## Pairing and ranges

| Method | Notes |
| ------ | ----- |
| `xs.enumerate(start: 0)` | array of `(index, value)` pairs |
| `xs.zip(ys, ..., exact: false)` | elementwise zip with one or more arrays |
| `array.range(end)` / `range(start, end, step: ...)` | also exposed at the top level as `range(...)` |
| `xs.to-dict()` | turn `((k, v), (k2, v2), ...)` into a dictionary |

```typst
#for (i, c) in ("A", "B", "C").enumerate() [#i: #c \ ]
#(1, 2).zip((10, 20), (100, 200))      // ((1,10,100), (2,20,200))
#range(5)                              // (0, 1, 2, 3, 4)
#range(2, 10, step: 3)                 // (2, 5, 8)
```

## Constructor

`array(value)` converts a `bytes`, `version`, or another `array` to an
array. **Don't** use it to build arrays from literals — use the
parenthesized syntax (`(1, 2, 3)`).

## When to use methods vs the global `range`

`range(...)` and `array.range(...)` are the same function, exposed
both globally and on the array type. Prefer the global form — it reads
like `for i in range(10)`.

## Practical tips

- **Iteration order** matches insertion order (and slice/sort order).
- **`.first()` / `.last()`** are convenience for `.at(0)` / `.at(-1)`
  and accept a `default:` to avoid erroring on empty arrays.
- **In-place mutators** (`push`, `pop`, `insert`, `remove`) require the
  array to live in a `let` (not in a literal). They return `none`
  unless explicitly designed to return a value (`pop`, `remove`).
- **Use `.fold`/`.reduce` over manual loops** when you can — Typst can
  optimize them better and the intent is clearer.
- For sorting by multiple keys, return a tuple from `key`:
  `xs.sorted(key: it => (it.priority, it.name))`.
