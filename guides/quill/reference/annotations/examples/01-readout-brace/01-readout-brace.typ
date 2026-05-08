// Annotations 01 — readout brace + label.

#import "@preview/quill:0.7.2": *
#set page(width: auto, height: auto, margin: 6pt)

#quantum-circuit(
  circuit-padding: (top: 16pt, default: 4pt),
  1, ctrl(1), $H$, meter(), [\ ],
  1, targ(),  1,    meter(),
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
