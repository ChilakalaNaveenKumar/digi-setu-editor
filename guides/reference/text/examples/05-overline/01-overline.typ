// 'overline(body, stroke: auto, offset: auto, extent: 0pt, evade: true,
//           background: false)' draws a line above text.
//
// Field cheat sheet (shared with 'underline' and 'strike'):
//   stroke      auto | stroke value     auto = font color + font-defined thickness
//   offset      auto | length           position relative to baseline
//   extent      length                  extra width on each side (negative = trim)
//   evade       bool                    skip sections where line would cross glyphs
//   background  bool                    place line BEHIND or in FRONT of glyphs

= Default

#overline[A line over text.]

= Custom stroke

#set text(fill: olive)
#overline(stroke: green.darken(20%) + 1pt, offset: -12pt)[The Forest Theme]

#set text(fill: black)

= 'extent' for tighter / wider lines

#overline(extent: -2pt)[Trimmed inward] \
#overline(extent: 4pt)[Extended outward]

= 'evade' (default true: line skips ascenders that would intersect)

evade true:  #overline(evade: true)[Tlbf rising letters] \
evade false: #overline(evade: false)[Tlbf rising letters]

= 'background: true' (line behind glyphs) -- visible when stroke is thick

#overline(stroke: (thickness: 1em, paint: maroon, cap: "round"), background: true)[Stylized] \
#overline(stroke: (thickness: 1em, paint: maroon, cap: "round"), background: false)[Hidden by line]
