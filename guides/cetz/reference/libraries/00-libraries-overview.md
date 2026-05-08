# Libraries — Overview

CeTZ ships several higher-level libraries on top of the core draw primitives.
Each is its own sub-module accessed as `cetz.<lib>.<fn>(...)`.

| Library | Purpose | Folder |
| ------- | ------- | ------ |
| Angle | Angle and right-angle decorators between two lines | [`angle/`](./angle/) |
| Tree | Layout-and-render rooted trees | [`tree/`](./tree/) |
| Decorations · Path | Wave-style replacements for an existing path (zigzag, coil, wave, square) | [`decorations/path/`](./decorations/path/) |
| Decorations · Brace | Curly braces between two points | [`decorations/brace/`](./decorations/brace/) |
| Palette | Style cycling helper for series of elements | [`palette/`](./palette/) |

These libraries are not auto-imported by `cetz.draw: *` — call them with the
fully-qualified path (`cetz.angle.angle(...)`, `cetz.tree.tree(...)`, …).
