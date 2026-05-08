# `util.lpad()` — Left-Pad a String with Zeros

Pads a string on the left with `0`s to the given length.

```text
#util.lpad("0100", 8)   // → "00000100"
```

## Signature

```text
lpad(
  string: str,
  len:    int,
) -> str
```

## Parameters

- **`string`** — `str`. The string to pad.
- **`len`** — `int`. The target length (in characters). If `string` is
  already at least that long, it is returned unchanged.

## Pitfalls

- Always pads with the literal character `0`. There is no `pad-with`
  argument.
- This is *content-level* padding — typically used to format binary port
  indices like `"00"`, `"01"`, `"10"`, `"11"` for a 4-input multiplexer.

## Example

See [`examples/01-lpad/01-lpad.typ`](./examples/01-lpad/01-lpad.typ).

## Related

- [`../element/05-multiplexer.md`](../element/05-multiplexer.md) — uses
  `lpad`-style binary labels when `entries:` is an integer.
