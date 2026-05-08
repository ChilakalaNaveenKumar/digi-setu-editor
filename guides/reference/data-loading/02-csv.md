# `csv()` — Reading CSV Files

`csv` parses comma-separated values (or any single-character delimiter)
into a 2-D structure of strings.

## Signature

```text
csv(
  source:    str | bytes,
  delimiter: str = ",",                  // single ASCII character
  row-type:  type = array,               // `array` (default) or `dictionary`
) -> array<array<str>> | array<dictionary<str, str>>
```

## Two row-types

### `row-type: array` (default)

Each row becomes an `array<str>`. Header rows are **not** stripped — the
first row is just another array of strings.

```typst
#let rows = csv("results.csv")           // (("a", "b"), ("1", "2"), ...)
#table(columns: rows.first().len(), ..rows.flatten())
```

### `row-type: dictionary`

Each row becomes a `dictionary<str, str>` keyed by the header row. The
header row is consumed and not part of the result.

```typst
#let rows = csv("people.csv", row-type: dictionary)
#for r in rows [
  - #r.name (#r.country): #r.email
]
```

This is the cleaner option whenever your CSV has a header row.

## Notes

- All values are returned as **strings** — Typst doesn't auto-detect
  numeric types. Convert with `int(...)` / `float(...)` as needed.
- `delimiter` must be a single ASCII character (e.g. `";"` or `"\t"`).
- For tab-separated files, use `delimiter: "\t"`.
- `csv.decode(...)` is **deprecated** — pass bytes directly to `csv(...)`.

## Recipe: typed columns

```typst
#let raw = csv("results.csv", row-type: dictionary)
#let typed = raw.map(r => (
  name:   r.name,
  amount: int(r.amount),
  share:  float(r.share),
))
```

A small `.map(...)` lets you keep the loader simple while getting
proper Typst types downstream.
