#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/cetz:0.5.0"

// NOTE: cetz 0.5.0 has a typo (`messaged:` instead of `message:`) inside
// `matrix.diag`, so the function is currently unusable. We construct the
// equivalent matrix by hand here.
#let diag(..diag) = {
  let entries = diag.pos()
  let n = entries.len()
  let m = ()
  for i in range(n) {
    let row = ()
    for j in range(n) {
      row.push(if i == j { entries.at(i) } else { 0 })
    }
    m.push(row)
  }
  m
}

#cetz.canvas({
  import cetz.draw: *
  let m = diag(1, 2, 3)
  content((0, 0), [diag(1, 2, 3) = #repr(m)])
})
