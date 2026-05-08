#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/circuiteria:0.2.0"
// `draw.*` is not re-exported by circuiteria; bring it in explicitly to
// drop the reference dots and labels around the wires.
#import "@preview/cetz:0.3.2": draw

#circuiteria.circuit({
  import circuiteria: *
  for i in range(3) {
    draw.circle((i * 3, 0),     radius: .1, name: "p" + str(i * 2))
    draw.circle((i * 3 + 2, 1), radius: .1, name: "p" + str(i * 2 + 1))
    draw.content((i * 3 + 1, -1), raw(wire.wire-styles.at(i)))
  }
  wire.wire("w1", ("p0", "p1"), style: "direct")
  wire.wire("w2", ("p2", "p3"), style: "zigzag")
  wire.wire("w3", ("p4", "p5"), style: "dodge",
    dodge-y: -0.5, dodge-margins: (0.5, 0.5))
})
