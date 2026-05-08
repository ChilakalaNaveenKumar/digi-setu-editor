#set page(width: 14cm, height: auto, margin: 1cm)

== Code block joins its outputs

#{
  let a = [from]
  let b = [*world*]
  [hello ]
  a + [ the ] + b
}

== Content block as a value

#let greeting = [*Hello*, world!]
#greeting \ \
First half: #text(fill: blue, greeting)

== Custom function (`let f(x) = ...`)

#let inc(x) = x + 1
#let greet(name, greeting: "Hello") = [#greeting, #name!]

inc(4) = #inc(4) \
greet("Ada"): #greet("Ada") \
greet("Bea", greeting: "Hi"): #greet("Bea", greeting: "Hi")

== Destructuring let

#let (x, y) = (1, 2)
#let (a, .., b) = (1, 2, 3, 4)
#let (Austen, ..rest) = (
  Austen: "Persuasion",
  Homer: "The Odyssey",
  Hugo: "Les Mis",
)

x=#x, y=#y, a=#a, b=#b \
Austen wrote #Austen, others: #rest.keys().join(", ")
