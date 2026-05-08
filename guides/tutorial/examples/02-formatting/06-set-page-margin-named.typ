// Demonstrates: per-side margin dictionary keys: left, right, top, bottom.
// Use this when sides differ (e.g. wider inside margin for binding).

#set page(
  paper: "a6",
  margin: (left: 2.4cm, right: 1.2cm, top: 1.5cm, bottom: 1.8cm),
)

= Per-Side Margins
Asymmetric margins are useful for bound documents
where the inside (gutter) margin needs more room.
