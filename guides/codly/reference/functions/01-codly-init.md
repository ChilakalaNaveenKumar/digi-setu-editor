# `codly-init` — The Show Rule

The show rule that activates Codly. Apply it **exactly once** near the
top of every document that wants Codly-styled code blocks:

```typst
#import "@preview/codly:1.3.0": *
#show: codly-init
```

## Signature

```text
codly-init(body) -> content
```

It is intended to be applied via Typst's `show: <function>` form, not
called directly.

## What it does

- Installs the `show raw.where(block: true): ...` rule that re-renders
  every block-style raw element with the Codly grid layout (line numbers,
  zebra stripes, language pill, header / footer, …).
- Installs a custom `show ref: ...` rule that resolves
  `@<label>:<n>`-style references to lines / highlights / annotations
  (see [`../../tutorial/02-referencing.md`](../../tutorial/02-referencing.md)).

## Pitfalls

- **Without `#show: codly-init`, every `codly(...)` call is a silent
  no-op.** Forgetting this line is the most common Codly bug.
- The show rule applies to *every* `raw(block: true)` in the document
  from this point on. Use [`no-codly`](./06-no-codly.md) or
  [`local(enabled: false, body)`](./05-local.md) to opt out per block.
- `codly-init` does **not** touch *inline* raw elements
  (`raw(block: false)`) — only block ones.

## Example

See [`examples/01-codly-init/01-codly-init.typ`](./examples/01-codly-init/01-codly-init.typ).

## Related

- [`../codly/01-codly.md`](../codly/01-codly.md) — configure what the
  show rule renders.
- [`../../tutorial/01-getting-started.md`](../../tutorial/01-getting-started.md)
  — full first-principles walkthrough.
