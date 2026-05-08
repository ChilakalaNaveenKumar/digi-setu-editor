// Search methods all take a "pattern" = either a string OR a regex.
//
//   .contains(pat)        -> bool   (also: 'pat in str' shorthand)
//   .starts-with(pat)     -> bool
//   .ends-with(pat)       -> bool
//   .find(pat)            -> str | none   first match as a substring
//   .position(pat)        -> int | none   BYTE index of the first match
//
// The 'in' operator is a shorthand: '"bc" in "abcd"' == '"abcd".contains("bc")'.
// 'in' also accepts a regex on the LHS: 'regex("\d+") in "10 euros"'.

#let s = "The quick brown fox jumps over 13 lazy dogs."

`contains "fox"`:          #s.contains("fox")
`"fox" in s`:              #("fox" in s)
`regex("\d+") in s`:       #(regex("\d+") in s)

`starts-with "The"`:       #s.starts-with("The")
`ends-with "."`:           #s.ends-with(".")
`ends-with regex(...)`:    #s.ends-with(regex("dogs\."))

`find "lazy"`:             #s.find("lazy")
`position "lazy"`:         #s.position("lazy")
`find regex("\d+")`:       #s.find(regex("\d+"))
`position regex("\d+")`:   #s.position(regex("\d+"))

`find missing`:            #s.find("nope")
`position missing`:        #s.position("nope")
