// Integration — CeTZ in callback style (no reducer).
#import "@preview/touying:0.7.3": *
#import "@preview/cetz:0.5.0"
#import themes.simple: *

#show: simple-theme.with(aspect-ratio: "16-9")

#slide(repeat: 3, self => [
  #let (uncover, only, alternatives) = utils.methods(self)

  Cetz in Touying in subslide #self.subslide:

  #cetz.canvas({
    import cetz.draw: *
    let uncover = uncover.with(cover-fn: hide.with(bounds: true))

    rect((0, 0), (5, 5))
    uncover("2-3", {
      rect((0, 0), (1, 1))
      rect((1, 1), (2, 2))
      rect((2, 2), (3, 3))
    })
    only(3, line((0, 0), (2.5, 2.5), name: "line"))
  })
])
