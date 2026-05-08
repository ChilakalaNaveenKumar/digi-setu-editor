#set page(width: 14cm, height: auto, margin: 1cm)

== Default array-of-arrays

#let rows = csv("_assets/people.csv")
First row (header): #raw(repr(rows.first())) \
Total rows including header: #rows.len()

#table(
  columns: rows.first().len(),
  ..rows.flatten().map(s => [#s]),
)

== Dictionary rows (header consumed)

#let people = csv("_assets/people.csv", row-type: dictionary)
#for p in people [
  - *#p.name* (#p.country), age #p.age
]

== Typed projection

#let typed = people.map(p => (
  name:    p.name,
  country: p.country,
  age:     int(p.age),
))

Average age: #(typed.map(p => p.age).sum() / typed.len())
