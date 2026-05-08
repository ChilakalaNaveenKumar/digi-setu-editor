// Theme — University.
#import "@preview/touying:0.7.3": *
#import themes.university: *
#import "@preview/numbly:0.1.0": numbly

#show: university-theme.with(
  aspect-ratio: "16-9",
  config-info(
    title: [University Demo],
    subtitle: [Three-column footer],
    author: [Touying Agent],
    date: datetime.today(),
    institution: [touying-typ],
    logo: emoji.school,
  ),
)
#set heading(numbering: numbly("{1}.", default: "1.1"))

#title-slide(authors: ([Author A], [Author B]))

= The Section
== Slide Title
#lorem(40)

#focus-slide[
  Another variant with primary color in background...
]

#matrix-slide[ left ][ middle ][ right ]
#matrix-slide(columns: 1)[ top ][ bottom ]
#matrix-slide(columns: (1fr, 2fr, 1fr), ..(lorem(8),) * 9)
