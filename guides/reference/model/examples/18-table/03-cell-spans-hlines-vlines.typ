// 'table.cell' (or 'cell' if you import it) gives per-cell control:
//   colspan, rowspan, fill, align, inset, stroke, breakable, x, y
//
// 'table.hline' and 'table.vline' draw lines that can cross gutter spacing
// and override per-cell strokes.
//
// 'table.header' marks header rows (repeats across pages by default).
// 'table.footer' marks footer rows (likewise repeats by default).

#import table: cell, header, footer

#set table(stroke: 0.5pt + gray)
#show table.cell.where(y: 0): strong

#table(
  columns: 4,
  header(
    [Substance], [Sub-critical °C], [Super-critical °C], [Notes],
  ),
  [Hydrochloric Acid], [12.0], [92.1], [Common reagent],
  [Sodium Myreth Sulfate], [16.6], [104], [Detergent],
  [Potassium Hydroxide], cell(colspan: 2)[24.7], [Strong base],
  footer(
    cell(colspan: 4, align: right)[_Source: lab notebook, 2026._],
  ),
)

= Manual hlines and vlines

#table(
  stroke: none,
  columns: (auto, 1fr),
  [09:00], [Badge pick up],
  [09:45], [Opening Keynote],
  [10:30], [Talk: Typst's Future],
  table.hline(start: 1),
  [Noon], [_Lunch break_],
  table.hline(start: 1),
  [14:00], [Talk: Tracked Layout],
  [15:00], [Talk: Automations],
  table.hline(),
  [19:00], [Day 1 Attendee Mixer],
)
