// 'mat(...rows; ..., delim: ("(", ")"), align: center, augment: none,
//      gap: 0pt, row-gap: 0.2em, column-gap: 0.5em)'
// renders a matrix.
//
// Inside math calls, ',' separates COLUMNS and ';' separates ROWS.
// Trailing ';' is allowed.

= Standard matrix

$ mat(
  1, 2, ..., 10;
  2, 2, ..., 10;
  dots.v, dots.v, dots.down, dots.v;
  10, 10, ..., 10;
) $

= Custom delimiter and alignment

#set math.mat(delim: "[", align: right)
$ mat(
  -1, 1, 1;
   1, -1, 1;
   1, 1, -1;
) $
#set math.mat(delim: ("(", ")"), align: center)

= Row gap, column gap

#set math.mat(row-gap: 1em, column-gap: 1em)
$ mat(1, 2; 3, 4) $
#set math.mat(row-gap: 0.2em, column-gap: 0.5em)
