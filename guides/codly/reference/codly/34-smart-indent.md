# `smart-indent`

Whether to use smart indentation: Codly checks for indentation on each
line and uses a *bigger left-side inset* instead of leading spaces. This
allows for line-breaks to continue at the same indentation level.

On by default; **disabling it can improve performance**.

| Field | Value |
| ----- | ----- |
| Type | `bool` |
| Default | `true` |
| Contextual function | no |
| Automatically reset | no |
| Released in 1.3.1 | yes |

## Example

```typst
*Enabled (default):*
```py
def quicksort(L):
  qsort = lambda L: [] if L==[] else qsort([x for x in L[1:] if x< L[0]]) + L[0:1] + qsort([x for x in L[1:] if x>=L[0]])
  qsort(L)
```

*Disabled:*
#codly(smart-indent: false)
```py
def quicksort(L):
  qsort = lambda L: [] if L==[] else qsort([x for x in L[1:] if x< L[0]]) + L[0:1] + qsort([x for x in L[1:] if x>=L[0]])
  qsort(L)
```
```

See [`examples/34-smart-indent/34-smart-indent.typ`](./examples/34-smart-indent/34-smart-indent.typ).

## Pitfalls

- The visual difference is most obvious for very long indented lines
  that wrap. For short or non-indented blocks the setting is invisible.

## Related

- [`19-inset.md`](./19-inset.md).
