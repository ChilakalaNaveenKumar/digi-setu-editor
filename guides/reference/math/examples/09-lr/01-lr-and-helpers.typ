// 'lr' family: scale delimiters to match content height.
//
// Matched delimiter pairs scale automatically:
//   $ [a, b/2] $       brackets stretch around the fraction
// 'lr(...)' lets you scale UN-matched delimiters or control the size:
//   $ lr(]sum_(x=1)^n], size: #50%) x $
//
// Helpers built on top of lr:
//   abs(x)     |x|
//   norm(x)    ||x||
//   floor(x)   ⌊x⌋
//   ceil(x)    ⌈x⌉
//   round(x)   ⌊x⌉   (rounds to nearest)
//   mid(x)     scale a delimiter to the SURROUNDING lr() group's height
//
// To DISABLE auto-scaling globally:  #set math.lr(size: 1em)
// To skip a specific delimiter from being matched: escape it with '\'.

= Auto-matched delimiters

$ [a, b / 2] $

= Custom-scaled delimiters

$ lr(]sum_(x=1)^n], size: #50%) x $

= Helpers

$ abs((x + y) / 2) $
$ norm(v) = sqrt(v dot v) $
$ floor(x / 2) quad ceil(x / 2) quad round(x / 2) $

= Set-builder using mid()

$ { x mid(|) sum_(i=1)^n w_i abs(f_i (x)) < 1 } $

= Escaping a delimiter to disable matching

$ \{ (x / y) \} $
// '\{' and '\}' are escaped so Typst does not match them and stretch them.

= Globally disable auto-scaling

#set math.lr(size: 1em)
$ { (a / b), a, b in (0; 1/2] } $
