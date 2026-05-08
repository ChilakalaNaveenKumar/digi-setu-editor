// Tutorial 10 — annotations.
// (1) Brace + label above two columns of a readout circuit.
// (2) Filled polygon spanning three cell centres.

#import "@preview/quill:0.7.2": *
#set page(width: auto, height: auto, margin: 6pt)

#quantum-circuit(
  1, ctrl(1), $H$, meter(), [\ ],
  1, targ(), 1, meter(),
  annotate((2, 4), 0, ((x1, x2), y) => {
    let brace = math.lr($#block(height: x2 - x1)}$)
    place(dx: x1, dy: y, rotate(brace, -90deg, origin: top))
    let lab = [Readout circuit]
    context {
      let size = measure(lab)
      place(
        dx: x1 + (x2 - x1) / 2 - size.width / 2,
        dy: y - .6em - size.height,
        lab,
      )
    }
  })
)

#v(0.8em)

#quantum-circuit(
  1, $X$, 2, [\ ],
  1, 2, $Y$, [\ ],
  1, 1, $H$, meter(),
  annotate((1.5, 3.5, 2.5), (0.5, 1.5, 2.5), z: "above",
    ((x0, x1, x2), (y0, y1, y2)) => {
    (
      content: polygon(
        (x0, y0), (x1, y1), (x2, y2),
        fill: rgb("#1020EE50"), stroke: .5pt + black
      ),
    )
  })
)
