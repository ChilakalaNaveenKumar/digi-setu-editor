# `local()` — One-Section Override

Locally override the global Codly settings for a specific block (or
section). Works by overriding the default Codly show rule locally with
the supplied arguments. **Does not rely on states** (much) and should
not add layout passes to the rendering, which can otherwise cause
documents to fail to converge.

## Signature

```text
local(
  ..codly-args,
  body:    content,
  nested:  bool = false,
) -> content
```

Accepts the same named arguments as [`codly(...)`](../codly/01-codly.md),
plus the `body:` (positional content) and the `nested:` flag.

## Example: simple override

```typst
*Global state with red color*
#codly(fill: red)
```typ
= Example
*Hello, World!*
```

*Locally set it to gray*
#local(
  fill: luma(240),
  ```typ
  = Example
  *Hello, World!*
  ```,
)

*It's back to being red*
```typ
= Example
*Hello, World!*
```
```

## Per-language configuration

`local` is the right tool for per-language styling, via a `show` rule on
raw blocks:

```typst
#show raw.where(block: true, lang: "rust"):
  local.with(number-format: numbering.with("I"))
```

Now every Rust block uses Roman numerals; everything else keeps the
global format.

You can also do this with a `show` rule that calls `codly(...)`, but
**you must manually reset the changes after each block**:

```typst
#show raw.where(block: true, lang: "py"): it => {
  codly(number-format: numbering.with("①"))
  it
  codly(number-format: numbering.with("1"))
}
```

The `local` route is faster and stateless; the `codly` route is more
flexible but slow and leaks settings if you forget the reset.

## Nested local state

Codly does support nested local state — the *innermost* `local` wins.
This allows different styles for different parts of the document.

```typst
#codly(fill: red)
```typ
*Red block*
```

#local(nested: true, fill: blue)[
  ```typ
  *Blue block*
  ```
  *Now green:*
  #local(nested: true, fill: green)[
    ```typ
    *Green block*
    ```
  ]
]

*Back to red:*
```typ
*Red block again*
```
```

> **Warning** — Nested local state with `nested: true` can slow down
> documents significantly if over-used. Use them sparingly. Setting
> `nested: false` (the default) on the outermost local is the
> cheap-but-less-flexible path; it means inner local states *override*
> rather than *layer*.
>
> **Info** — Once Typst supports custom elements, Codly will move to
> proper set rules and this limitation will be lifted.

See [`examples/05-local/05-local.typ`](./examples/05-local/05-local.typ).

## Pitfalls

- The default `nested: false` means the outermost local is overridden
  by inner ones (and any *previous* local states in the same hierarchy
  are ignored for subsequent blocks).
- Inside `show raw.where(...)` show rules, **prefer `local`** over a
  bare `codly(...)` call — `codly(...)` will leak.

## Related

- [`06-no-codly.md`](./06-no-codly.md),
  [`07-yes-codly.md`](./07-yes-codly.md),
  [`../codly/01-codly.md`](../codly/01-codly.md).
