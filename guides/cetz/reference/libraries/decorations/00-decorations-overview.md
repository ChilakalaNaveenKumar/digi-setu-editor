# Decorations Library — Overview

`cetz.decorations` decorates an existing path with a wave-style replacement
or wraps two points in a curly brace.

| Sub-library | Functions | Folder |
| ----------- | --------- | ------ |
| Path decorations | `zigzag`, `coil`, `wave`, `square` | [`path/`](./path/) |
| Brace decorations | `brace`, `flat-brace` | [`brace/`](./brace/) |

All path decorations share three style keys:

| Key | Meaning |
| --- | ------- |
| `segments` | Number of repetitions along the path |
| `segment-length` | …or set the length of one repetition; CeTZ picks the count |
| `amplitude` | Width of the wave perpendicular to the path |
| `start` / `stop` | `<percentage>` along the path to start / end the decoration |
