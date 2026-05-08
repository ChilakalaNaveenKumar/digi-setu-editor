// Annotations 03 — arrow overlay (no fancy arrowhead, plain line + label).

#import "@preview/quill:0.7.2": *
#set page(width: auto, height: auto, margin: 6pt)

#quantum-circuit(
  circuit-padding: (top: 22pt, default: 4pt),
  1, gate($H$), ctrl(1), 1, [\ ],
  1, 1, targ(), 1,
  annotate(2, 0, (x, y) => {
    let target = (x, y - 2pt)
    let label-pos = (x + 14pt, y - 18pt)
    place(
      dx: 0pt, dy: 0pt,
      curve(
        curve.move(label-pos),
        curve.line(target),
        stroke: 0.5pt + red,
      ),
    )
    place(
      dx: label-pos.at(0) + 2pt, dy: label-pos.at(1) - 8pt,
      text(red, size: 8pt)[*magic CNOT*],
    )
  })
)
