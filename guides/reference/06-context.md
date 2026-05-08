# Context – Reactive, Location-Aware Evaluation

Typst code by default doesn't know **where** in the document it ends
up. Some code at the start of the source can produce content placed
at the back of the document, after numbering, headings, layouts, etc.
have all been resolved. To compute things that depend on location or
on settable styles, you need to enter **context**.

## The `context` keyword

```typst
#set text(lang: "de")
#context text.lang        // → "de"
```

`context expr` makes the *one expression* opaque content. Typst
re-evaluates it whenever it is laid out — possibly multiple times,
at different positions — and uses the surrounding state at that
moment. From outside the context block you can't peek at the value;
you can only *use it as content*.

> **Why opaque?** Because there's no single right answer. The same
> context block placed in three different sections might compute
> three different values. Typst hides the value to keep that
> well-defined.

A context expression has access to two flavors of information:

1. **Style context** — settable element fields (`text.lang`,
   `text.size`, `heading.numbering`, etc.).
2. **Location context** — the current page, the location of any
   labelled element, results of `query(...)`, current counter and
   state values, physical positions via `locate(...)`.

## Style context

You can read any settable parameter as a *field* on its element
function, but only inside a context:

```typst
#let value = context text.lang
#value             // → "en" (default)

#set text(lang: "de")
#value             // → "de"

#set text(lang: "fr")
#value             // → "fr"
```

The `value` here is an opaque content value. Each placement re-runs
the body inside the surrounding style.

## Location context

Some functions implicitly depend on "where I am right now":

| Function                          | Needs context | Notes                                         |
| --------------------------------- | ------------- | --------------------------------------------- |
| `here()`                          | yes           | Returns the current `location`.               |
| `counter(x).get()`                | yes           | Counter value at current location.            |
| `counter(x).at(loc-or-label)`     | yes           | Counter value at a specific location.         |
| `locate(selector)`                | yes           | The location of the matched element.          |
| `query(selector)`                 | yes           | Array of elements matching the selector.      |
| `state.get()` / `state.at(loc)`   | yes           | Like `counter`, but for arbitrary state.      |
| `length.to-absolute()` (on `em`)  | yes           | Resolves relative-to-font lengths to absolute.|

```typst
#set heading(numbering: "1.")

= Introduction <intro>
= Background  <back>

#context [
  #counter(heading).get() \           // (2,)
  #counter(heading).at(here()) \      // (2,)
  #counter(heading).at(<intro>)       // (1,)
]
```

The `at(<label>)` form is the time-travel feature: from inside one
context block you can read the counter value as it was at any other
labeled element.

## Implicit context (show rules)

You don't always need an explicit `context`. Typst opens an implicit
context inside:

- **Show rules** for any element — they get style context.
- **Show rules for *locatable* elements** — they additionally get
  location context. (Most elements you'd target are locatable.)
- **Outline numberings** — to resolve heading counter values.

That's why `#show heading: it => [#it.body — page #here().page()]`
works without an outer `context` keyword.

## Nested contexts

Context blocks nest. The innermost context wins:

```typst
#set text(lang: "de")
#context [
  #set text(lang: "fr")
  #text.lang \              // "de" — outer context, set rule below it
  #context text.lang        // "fr" — inner context sees the new set rule
]
```

The first `text.lang` reads the **outer** context's styles, which
were captured before the `set text(lang: "fr")` line. The nested
`context` opens a fresh context whose snapshot includes the inner
set rule.

The same applies to location context: `counter` updates inside an
outer context block won't be visible to that block's other reads,
but a nested `context` *will* see them.

## Compiler iterations

To resolve `locate`, `query`, counter values, etc., Typst compiles
the document multiple times — first with placeholder values, then
again with the resolved layout, and so on. The convergence limit is
**5 iterations**; beyond that you'll see:

```
warning: layout did not converge within 5 attempts
```

If you hit this, look for state updates that depend on the very
results they produce (e.g. counters mutated inside their own context
block). Move the mutation outside or break the cycle with a fixed
intermediate.

## Pitfalls and idioms

- **Read element fields inside `context`, never at the top level.**
  Top-level `text.lang` is an error.
- **Templates that read state must enter context themselves.** The
  caller doesn't have to wrap the call in `context` — but the
  template's *implementation* does, anywhere it reads styles or
  locations.
- **Hoist captures, not contexts.** A `let value = context ...`
  binding is a perfectly fine way to define a "deferred reading" you
  can drop into multiple places.
- **Use `here()` over hand-built locations.** It's the safe way to
  refer to "wherever this code ends up". Combine with `at(<label>)`
  for cross-references.
- **Context blocks aren't free.** Each one re-runs every layout
  iteration; keep them small and put expensive computation outside.
