# `rect` — basic rectangle

The standard rectangle node shape. Picks `rect` automatically when the
node label is wider than tall (and you haven't set `node-shape` or
`shape:` explicitly).

## Signature

```typst
rect(node, extrude)
```

`node.size`, `node.corner-radius`, `node.stroke`, `node.fill` are
read; `extrude` is the offset for multi-stroke nodes.

## Equivalent ways to set

```typst
node([Hi], shape: rect)            // explicit shape function
node([Hi], shape: "rect")          // string alias
node([Hi], shape: std.rect)        // Typst's element function
```

## Example

```typst
#diagram(
  node-stroke: 1pt,
  node((0, 0), [Hello], shape: rect),
  node((1, 0), [World], shape: rect.with(), corner-radius: 3pt),
)
```

See [`examples/01-rect/01-rect.typ`](examples/01-rect/01-rect.typ).

## Pitfalls

- `corner-radius` is a *node* option, not a shape option — set it on
  `node(...)` rather than via `rect.with(...)`.
- The default `auto` shape may pick `circle` for square-ish labels;
  force `shape: rect` to keep rectangles.
