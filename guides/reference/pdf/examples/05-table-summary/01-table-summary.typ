// NOTE: Requires the `a11y-extras` feature flag:
//   typst compile --features a11y-extras 01-table-summary.typ

#set page(width: 14cm, height: auto, margin: 1cm)

#figure(
  pdf.table-summary(
    summary: "The first two columns list participants. The third column "
            + "uses rowspans to assign each contiguous group of "
            + "participants to one team.",
    table(
      columns: 3,
      table.header[First Name][Given Name][Group],
      [Mike], [Davis], table.cell(rowspan: 3)[Sales],
      [Anna], [Smith],
      [John], [Johnson],
      [Sara], [Wilkins], table.cell(rowspan: 2)[Operations],
      [Tom],  [Brown],
    ),
  ),
  caption: [The Sales org now has a new member.],
)
