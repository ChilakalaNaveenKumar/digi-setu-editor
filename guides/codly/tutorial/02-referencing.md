# 02 — Referencing Code Blocks, Highlights, and Annotations

> **Codly version:** 1.3.0 · **Source:** `docs.pdf` §3

This page covers Section 3 of the manual: how to reference *lines*,
*highlights*, and *annotations* from running prose using the standard
Typst `@label` reference syntax.

## Three preconditions

For any of the references below to work, **all three** of the following
must be true for the code block:

1. Numbering of figures must be turned on:

   ```typst
   #set figure(numbering: "1")
   ```

2. The code block must be wrapped in a `figure(kind: raw)` (Typst's
   default `figure` for raw blocks already uses `kind: raw`, so just put
   the block inside `#figure[...]`).

3. The figure must have its own label:

   ```typst
   #figure(caption: "...")[
     ```typ
     ...
     ```
   ] <my-label>
   ```

If any precondition is missing, the reference will silently render
"??" or fall back to a generic listing reference.

## Shorthand line references

Reference the *N-th line* (one-indexed) of a labelled code block with
`@<label>:<n>`:

```typst
#figure(caption: [Hello])[
  ```typ
  = Example
  *Hello, world!*
  ```
] <hello>

I can reference my code block: @hello.
Or a specific line:                @hello:2.
```

Renders to (approximately):

> I can reference my code block: **Listing 1**.
> Or a specific line:           **Listing 1-2**.

The separator (`-` by default) between the listing number and the line
number is controlled by [`reference-sep`](../reference/codly/52-reference-sep.md);
the line-number formatter is
[`reference-number-format`](../reference/codly/53-reference-number-format.md).

## Highlight references — `"line"` mode (default)

Give your highlight a `label:` and reference it the same way:

```typst
#codly(highlights: (
  (line: 2, start: 2, end: 7, label: <hl-1>),
))

#figure(caption: [Hello])[
  ```typ
  = Example
  * Hello, world! *
  ```
] <hello>

Reference a highlight by its label: @hl-1.
```

Renders to:

> Reference a highlight by its label: **Listing 1-2**.

(The reference is to the *line containing the highlight*, formatted with
`reference-number-format`.)

## Highlight references — `"item"` mode

When you set [`reference-by: "item"`](../reference/codly/51-reference-by.md),
references resolve to the *highlight's `tag:` content* instead of the line
number:

```typst
#codly(
  reference-by: "item",
  highlights: (
    (line: 2, start: 2, end: 7, label: <hl-2>, tag: [ Highlight ]),
  ),
)

#figure(caption: [Hello])[
  ```typ
  = Example
  * Hello, world! Highlight *
  ```
] <hello-2>

Reference a highlight by its label: @hl-2.
```

Renders to:

> Reference a highlight by its label: **Listing 1-Highlight**.

For this mode you **must** set the `tag:` on every tagged highlight you
plan to reference.

## Annotation references

Annotations work the same way: give the annotation a `label:` (only valid
when the block is inside a `figure(kind: raw)`) and reference it with
`@<label>`. The displayed text uses
[`reference-number-format`](../reference/codly/53-reference-number-format.md)
in `"line"` mode and
[`annotation-format`](../reference/codly/41-annotation-format.md) (or the
annotation's `content:` field) in `"item"` mode.

## Pitfalls

- **Numbered figures** (`set figure(numbering: ...)`) is the easiest
  precondition to forget. Without it, references silently fail.
- The label must be on the **figure**, not on the raw block. Put it
  *after* the closing bracket of the `#figure[...]` body.
- Highlight references in `"item"` mode require **both** `label:` and
  `tag:`. Either alone is not enough.
- The reference syntax is the standard Typst `@label`/`@label:n` syntax —
  Codly hooks into it via a custom `ref` show rule registered by
  `codly-init`.

## Related reference pages

- [`../reference/codly/51-reference-by.md`](../reference/codly/51-reference-by.md) —
  pick `"line"` vs `"item"` reference mode.
- [`../reference/codly/52-reference-sep.md`](../reference/codly/52-reference-sep.md) —
  customise the separator between the listing number and the line / item.
- [`../reference/codly/53-reference-number-format.md`](../reference/codly/53-reference-number-format.md) —
  customise how the line number is rendered (Roman, circled, etc.).
- [`../reference/codly/40-annotations.md`](../reference/codly/40-annotations.md),
  [`../reference/codly/44-highlights.md`](../reference/codly/44-highlights.md) —
  how to set the `label:` on annotations and highlights so this page's
  references resolve.
