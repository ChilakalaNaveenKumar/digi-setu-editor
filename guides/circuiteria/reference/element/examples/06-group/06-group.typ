#set page(width: 14cm, height: auto, margin: 8pt)
#import "@preview/circuiteria:0.2.0"

#circuiteria.circuit({
  import circuiteria: *
  element.group(
    id: "g1", name: "Group 1", stroke: (dash: "dashed"),
    {
      element.block(id: "b1", w: 2, h: 2,
        x: 0, y: 1.5,
        ports: (east: ((id: "out"),)),
        fill: util.colors.green,
      )
      element.block(id: "b2", w: 2, h: 1,
        x: 0, y: 0,
        ports: (east: ((id: "out"),)),
        fill: util.colors.orange,
      )
    },
  )
  element.block(id: "b3", w: 2, h: 3,
    x: (rel: 1, to: "g1.east"),
    y: (from: "b1-port-out", to: "in1"),
    ports: (west: ((id: "in1"), (id: "in2"))),
    fill: util.colors.blue,
  )
  wire.wire("w1", ("b1-port-out", "b3-port-in1"))
  wire.wire("w2", ("b2-port-out", "b3-port-in2"),
    style: "zigzag")
})
