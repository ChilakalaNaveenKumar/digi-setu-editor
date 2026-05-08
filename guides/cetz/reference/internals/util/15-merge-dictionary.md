# `util.merge-dictionary()` — Recursive Dictionary Merge

Recursively merges two dictionaries — fields that are themselves
dictionaries are merged in turn. By default values in `b` overwrite
matching keys in `a`.

## Signature

```text
merge-dictionary(a: dictionary, b: dictionary, overwrite: bool = true) -> dictionary
```

## Parameters

- **`a`** — base dictionary.
- **`b`** — dictionary to fold in.
- **`overwrite`** — if `false`, existing keys in `a` are preserved.

## Example

See [`examples/15-merge-dictionary/15-merge-dictionary.typ`](./examples/15-merge-dictionary/15-merge-dictionary.typ).
