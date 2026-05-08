#set page(width: 14cm, height: auto, margin: 1cm)

== if / else if / else

#let classify(x) = if x > 0 [positive] else if x < 0 [negative] else [zero]

#classify(3) \
#classify(-2) \
#classify(0)

== for loop joining string output

#for c in "ABC" [#c is a letter. \ ]

== for over an array of tuples (with destructuring)

#for (k, v) in (a: 1, b: 2, c: 3) [#k = #v \ ]

== while + array accumulation

#let powers = ()
#let n = 1
#while n <= 16 {
  powers.push(n)
  n = n * 2
}
Powers of two up to 16: #powers

== break / continue

#for letter in "abc nope" {
  if letter == " " { break }
  letter
}
