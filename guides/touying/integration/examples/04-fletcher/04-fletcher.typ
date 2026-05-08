// Integration — Fletcher via touying-reducer.
#import "@preview/touying:0.7.3": *
#import themes.metropolis: *
#import "@preview/fletcher:0.5.8" as fletcher: node, edge

#let fletcher-diagram = touying-reducer.with(
  reduce: fletcher.diagram,
  cover: fletcher.hide,
)

#show: metropolis-theme.with(
  aspect-ratio: "16-9",
  config-info(title: [Fletcher Integration]),
)

#title-slide()

== Animated Fletcher
#slide[
  #fletcher-diagram(
    node-stroke: .1em,
    node-fill: gradient.radial(
      blue.lighten(80%), blue,
      center: (30%, 20%), radius: 80%,
    ),
    spacing: 4em,
    edge((-1, 0), "r", "-|>", `open(path)`,
         label-pos: 0, label-side: center),
    node((0, 0), `reading`, radius: 2em),
    edge((0, 0), (0, 0), `read()`, "--|>", bend: 130deg),
    pause,
    edge(`read()`, "-|>"),
    node((1, 0), `eof`, radius: 2em),
    pause,
    edge(`close()`, "-|>"),
    node((2, 0), `closed`, radius: 2em, extrude: (-2.5, 0)),
    edge((0, 0), (2, 0), `close()`, "-|>", bend: -40deg),
  )
]
