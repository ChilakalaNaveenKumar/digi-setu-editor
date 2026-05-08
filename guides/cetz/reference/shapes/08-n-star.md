# `n-star()` — N-Pointed Star

Draws an n-pointed star.

## Signature

```text
n-star(
  origin: coordinate,
  sides:  int,
  angle:  angle,
  name:   none | str = none,
  anchor: ,
  ..style,
)
```

## Parameters

- **`origin`** — centre of the star.
- **`sides`** — number of points (`>= 3`).
- **`angle`** — rotation around `origin`.
- **`name`** — optional element name.
- **`radius`** *(style)* — radius of the **outer** points.
- **`inner-radius`** *(style)* — `number | ratio`. Inner-point radius. If a
  ratio it is relative to the outer radius.
- **`show-inner`** *(style)* — `bool`. When `true`, also draws the inner
  polygon connecting the inner points.
- **`fill`** *(style)* — fill color (or gradient).
- **`stroke`** *(style)* — stroke for the star and the inner polygon.

## Styling

- **Root:** `nstar` (note: no hyphen).

## Anchors

Path anchors + compass border anchors.

## Example

See [`examples/08-n-star/08-n-star.typ`](./examples/08-n-star/08-n-star.typ).
