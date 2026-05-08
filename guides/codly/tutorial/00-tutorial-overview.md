# Codly Tutorial — Overview

Read these in order before diving into the per-argument pages under
[`../reference/`](../reference/).

| File | Covers |
| ---- | ------ |
| [`01-getting-started.md`](./01-getting-started.md) | Importing the package, the `#show: codly-init` show rule, the `codly(...)` configuration model (set-rule semantics, `local`, the auto-reset flag), the manual's "info card" notation. |
| [`02-referencing.md`](./02-referencing.md) | Section 3 of the manual — referencing lines (`@my-label:2`), highlights, and annotations. The three preconditions for it to work (numbered figures, `kind: raw`, label on the figure). |

After this you should be comfortable navigating any argument under
`../reference/codly/` and any helper under `../reference/functions/`. Each
page assumes you know:

1. **Codly is initialised once** at the top of the document with
   `#show: codly-init`. Without it, `codly(...)` is a silent no-op.
2. **`codly(...)` is set-rule-like, not show-rule-like.** It writes
   into Typst states; the configuration applies to *every* following code
   block in layout order until you call `codly(...)` again,
   `codly-reset()`, or wrap a block in `local(...)`.
3. **Some arguments auto-reset after each block, some don't.** The
   manual's "info card" tells you which; each reference page restates the
   five card fields verbatim (type / default / contextual / auto-reset /
   released-in).
