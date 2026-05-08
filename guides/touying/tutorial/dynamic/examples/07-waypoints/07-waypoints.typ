// Dynamic 07 — Named waypoints.
#import "@preview/touying:0.7.3": *
#import themes.simple: *

#show: simple-theme.with(aspect-ratio: "16-9")

== Basic waypoints
#slide[
  Base content.
  #waypoint(<step-a>)
  #uncover(<step-a>)[Uncovered from step-a.]
  #waypoint(<step-b>)
  #only(<step-b>)[Only during step-b.]
]

== Waypoint markers
#slide[
  #waypoint(<mid>)
  #uncover(<mid>)[Visible during mid.]
  #waypoint(<end>)
  #uncover(from-wp(<mid>))[From mid onward.]
  #only(prev-wp(<end>))[Only before end starts.]
]
