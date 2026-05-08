// Multi-file architecture — main entry point.
// Applies the theme and includes content.typ.
#import "globals.typ": *

#show: simple-theme.with(
  aspect-ratio: "16-9",
  footer: [Multi-file demo],
  config-info(
    title: [Multi-file Touying],
    author: [Agent],
    date: datetime.today(),
    institution: [Touying docs],
  ),
)

#include "content.typ"
