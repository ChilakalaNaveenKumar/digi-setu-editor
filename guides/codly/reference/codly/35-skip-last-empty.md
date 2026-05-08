# `skip-last-empty`

Whether to automatically skip the last line of the code block if it is
empty. This avoids having an unnecessary empty line at the end of the
code block (a common artefact when copy-pasting source).

| Field | Value |
| ----- | ----- |
| Type | `bool` |
| Default | `true` |
| Contextual function | yes |
| Automatically reset | no |
| Released in 1.3.1 | yes |

## Example

```typst
*Enabled (default):*
```py
def fib(n):
  if n <= 1:
    return n
  return fib(n - 1) + fib(n - 2)

```
*Disabled:*
#codly(skip-last-empty: false)
```py
def fib(n):
  if n <= 1:
    return n
  return fib(n - 1) + fib(n - 2)

```
```

See [`examples/35-skip-last-empty/35-skip-last-empty.typ`](./examples/35-skip-last-empty/35-skip-last-empty.typ).
