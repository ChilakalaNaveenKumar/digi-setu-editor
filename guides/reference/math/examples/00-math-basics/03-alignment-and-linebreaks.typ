// LINE BREAKS in math: use '\' (same as text-mode line break).
//
// ALIGNMENT POINTS: '&' creates an alignment column. Each successive '&'
// alternates RIGHT-aligned then LEFT-aligned.
//   ... &= ...     -> '=' aligns to the left, expression to its right
//   ... &= ... && "comment"
//                  -> the comment becomes its own LEFT-aligned column
// So '& &' (or '&&') just consumes two slots without splitting the column.

$ sum_(k=0)^n k
    &= 1 + 2 + dots + n \
    &= (n(n+1)) / 2 $

$ (3x + y) / 7  &= 9 && "given" \
  3x + y        &= 63   & "multiply by 7" \
  3x            &= 63 - y && "subtract y" \
  x             &= (63 - y) / 3 & "divide by 3" $
