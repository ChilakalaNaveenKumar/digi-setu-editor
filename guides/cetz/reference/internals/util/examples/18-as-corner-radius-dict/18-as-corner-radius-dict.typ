#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

// `as-corner-radius-dict` underlies the `radius:` option on `rect`. The
// most reliable form in cetz 0.5.0 is a single scalar applied to every
// corner.
#cetz.canvas({
  import cetz.draw: *
  rect((0, 0), (1.5, 0.6), radius: 0.2)
  rect((2, 0), (3.5, 0.6), radius: 0.05)
})
