// NOTE: Requires the `a11y-extras` feature flag:
//   typst compile --features a11y-extras 01-header-cell.typ

#set page(width: 14cm, height: auto, margin: 1cm)

#show table.cell.where(x: 0): set text(weight: "medium")
#show table.cell.where(y: 0): set text(weight: "bold")

#table(
  columns: 3,
  align: (start, end, end),

  table.header(
    // Top-left labels both rows and columns.
    pdf.header-cell(scope: "both")[Nutrient],
    [Per 100g],
    [Per Serving],
  ),

  pdf.header-cell(scope: "row")[Calories], [250 kcal], [375 kcal],
  pdf.header-cell(scope: "row")[Protein],  [8g],       [12g],
  pdf.header-cell(scope: "row")[Fat],      [12g],      [18g],
  pdf.header-cell(scope: "row")[Carbs],    [30g],      [45g],
)
