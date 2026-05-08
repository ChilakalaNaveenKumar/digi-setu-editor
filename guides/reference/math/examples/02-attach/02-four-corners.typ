// 'attach(base, t: ?, b: ?, tl: ?, tr: ?, bl: ?, br: ?)' attaches things
// to up to FOUR corners of the base PLUS the top/bottom slots.
//
//   t   top      (smart: sup or above)
//   b   bottom   (smart: sub or below)
//   tl  top-left            (always BEFORE the base, above)
//   bl  bottom-left         (always BEFORE the base, below)
//   tr  top-right           (always AFTER the base, above)
//   br  bottom-right        (always AFTER the base, below)
//
// 't:'/'b:' use smart positioning; the corner slots are always literal
// corner attachments (regardless of base type).

= All six slots

$ attach(
  Pi, t: alpha, b: beta,
  tl: 1, tr: 2 + 3,
  bl: 4 + 5, br: 6,
) $

= Tensor-style indices via tl/tr/bl/br

$ attach(R, tl: a, tr: b, bl: c, br: d) $

= Mixing shorthand with corner attachments

The shorthand `_` / `^` fills `b:` / `t:`. Combine with `attach()` for the
left corners:

$ attach(T, tl: mu, bl: nu)^alpha _beta $
