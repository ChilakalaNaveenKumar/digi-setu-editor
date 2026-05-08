# Introspection – Overview

Introspection is Typst's "look back at the document" toolkit. With it, you
can:

- Number things that aren't headings/figures (theorems, exercises, custom
  pages) — see [`counter`](./01-counter.md).
- Build tables of contents, lists of figures, indices — see
  [`query`](./06-query.md), [`location`](./04-location.md),
  [`locate`](./03-locate.md).
- Track per-document state (current chapter, accumulator) — see
  [`state`](./07-state.md).
- Expose values to the CLI for `typst query` — see
  [`metadata`](./05-metadata.md).
- Find out *where am I right now?* — see [`here`](./02-here.md).

## What lives in this module

| Function / Type | Purpose                                                    |
| --------------- | ---------------------------------------------------------- |
| `counter`       | Counters for pages, headings, figures, custom things.      |
| `state`         | Generic per-document mutable state.                        |
| `here`          | The current `location` inside a `context` block.           |
| `locate`        | Resolve a `selector` to a single element's `location`.     |
| `location`      | The type returned by `here()` / `locate()` / `.location()`. Has `.page()`, `.position()`, `.page-numbering()`. |
| `query`         | Find all elements matching a selector.                     |
| `metadata`      | Embed an invisible value (great for `typst query` CLI).    |

## The `context` requirement

Most of these operations are **contextual**: their result depends on
*where* in the document you call them, so they can only be evaluated once
Typst knows their position. You must call them inside `context { ... }`
(or `#context [...]`):

```typst
#context [I am on page #here().page().]
```

Three things are contextual:

1. **Reading state/counters/queries.** `counter(...).get()`, `state(...).get()`,
   `here()`, `query(...)`, `locate(...)`.
2. **Anything derived from styles.** `text.size`, `page.width`, etc.
3. **Layout-dependent measurement.** `measure(...)`.

Plain *updates* (`counter(...).step()`, `state(...).update(...)`) do **not**
require `context` — they just produce content that, when inserted into the
document, takes effect at that point.

## Locatable elements

Only certain elements have a stable, queryable location. As a rule:

- **Most `model` elements are locatable**: `heading`, `figure`, `outline`,
  `bibliography`, `cite`, `quote`, etc.
- **Decorative text elements** (`raw`, `underline`, `overline`, `strike`,
  `highlight`) are locatable too.
- `metadata`, `math.equation`, and `image` are locatable.
- Most other elements (paragraphs, plain text runs, layout helpers) are
  **not** locatable directly — attach a `<label>` to make them queryable.

If `query` returns nothing for what looks like the right selector, the
element type is probably not locatable.

## Pitfall: queries that affect themselves

Counters, state, and queries are resolved by re-running the document a few
times until things stabilize. If your query *generates* what it queries
for (e.g. a query that produces N headings every time it sees N headings),
Typst gives up after a few iterations and the result is whatever the loop
landed on.

Best practices:

- Don't spawn content from a `state.get()` that changes the very same
  state.
- When updating state from prior state, use the **function form**:
  `state(...).update(prev => prev + 1)` — it requires fewer iterations
  than reading via `context`.

## Time travel

`counter` and `state` both expose `.at(loc)` and `.final()` — the value at
a specific location, and the value at the document's end. This lets you
write things like "X / Y" page numbers and "current chapter" headers from
a single place.

## Keep `query` cheap

`query(heading)` walks the entire document. It's fine to call it once for
a TOC, but avoid calling it inside per-element show rules — that
explodes layout cost. Cache the result in a `let` outside the show rule.
