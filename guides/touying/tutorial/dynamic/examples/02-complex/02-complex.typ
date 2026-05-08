// Dynamic 02 — only / uncover / alternatives in callback style.
#import "@preview/touying:0.7.3": *
#import themes.simple: *

#show: simple-theme.with(aspect-ratio: "16-9")

== Mark style
At subslide #touying-fn-wrapper((self: none) => str(self.subslide)):
- #uncover("2-")[`#uncover` reserves space]
- #only("2-")[`#only` does not reserve space]
- #alternatives[Ann][Bob][Christopher]

== Callback style
#slide(repeat: 3, self => [
  #let (uncover, only, alternatives) = utils.methods(self)
  At subslide #self.subslide, we can:
  - use #uncover("2-")[`#uncover` for reserving space],
  - use #only("2-")[`#only` for not reserving space],
  - #alternatives[chocolate][strawberry][vanilla] ice cream.
])
