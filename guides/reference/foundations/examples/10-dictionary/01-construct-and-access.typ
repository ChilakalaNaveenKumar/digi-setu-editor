// Construction:
//   (key: value, ...)            -- normal literal. Keys are bare identifiers
//                                   OR string literals. Values may be any type.
//   (:)                          -- empty dictionary. (Plain '()' is an empty
//                                   ARRAY, not dict.)
//
// Access:
//   dict.key      field-access syntax (key must be a static identifier)
//   dict.at("k") method form (works with computed/dynamic keys)
//   "k" in dict  membership test (returns bool)
//
// Mutation:
//   dict.key = v          (key must already exist for field-assign)
//   dict.insert("k", v)   (creates or replaces)

#let empty = (:)
#let project = (name: "Typst", born: 2019)

empty len:           #empty.len()
project.name:        #project.name
project.at("born"):  #project.at("born")
"name" in project:   #("name" in project)
"city" in project:   #("city" in project)

#project.insert("city", "Berlin")
#(project.born = 2018)

after edits: #project
