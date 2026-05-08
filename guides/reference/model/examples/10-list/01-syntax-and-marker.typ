// 'list' (BULLET LIST):
//
// MARKUP SHORTHAND: a line starting with '- ' (hyphen + space). Indented
// content under a list item belongs to that item. Nest by indenting the
// marker further.
//
// Function form:
//   #list([item], [item], ...)
//   #list.item[body]    -- single item helper for programmatic construction
//
// Most-used fields:
//   marker       content | array | function     bullet glyph(s)
//                  array form: cycles per nesting depth
//                  function form: depth (0-based) -> content
//   tight        bool                          markup-driven; cannot be set
//                                                from set rules
//   indent       length                        per-item indent
//   body-indent  length                        gap between marker and body
//   spacing      auto | length                 between items

= Default list

- one
- two
- three with a longer line that wraps onto a second line because
  the next line is indented under the marker
  - nested A
  - nested B
- four

= Custom marker (single)

#set list(marker: [--])
- a more classic look
- with en-dashes

= Custom marker (cycling per depth)

#set list(marker: ([•], [--], [-]))
- top
  - second level
    - third level
- top again

= Function marker

#set list(marker: depth => if calc.even(depth) [▶] else [▷])
- depth 0
  - depth 1
    - depth 2
