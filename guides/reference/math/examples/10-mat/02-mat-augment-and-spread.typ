// AUGMENT: draw partition lines inside the matrix.
//   augment: 2                  -> single vertical line after column 2
//   augment: -1                 -> single vertical line after the last
//                                   column from the END (so 'second-last|last')
//   augment: (                  -> dictionary form: multiple lines + style
//     vline: <int|array>,
//     hline: <int|array>,
//     stroke: <stroke>,
//   )

= Augment via integer (vertical line)

$ mat(1, 0, 1; 0, 1, 2; augment: #2) $
// Same as augment: #(-1)
$ mat(1, 0, 1; 0, 1, 2; augment: #(-1)) $

= Augment via dictionary (custom hline + style)

$ mat(
  0, 0, 0;
  1, 1, 1;
  augment: #(hline: 1, stroke: 2pt + green),
) $

= Building a matrix from data programmatically

#let data = ((1, 2, 3), (4, 5, 6))
#let m = math.mat(..data)

$ A := m $

= Spread of an array of arrays inside a math call

$ mat(..#range(1, 5).chunks(2)) $
// range(1, 5) = (1, 2, 3, 4); .chunks(2) = ((1, 2), (3, 4))
// Spread becomes mat((1, 2), (3, 4)) -> 2x2 matrix.
