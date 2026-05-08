// A label attaches to the closest preceding non-space element in the same scope.
//
// Two ways to create one:
//   <name>           dedicated syntax. 'name' may contain letters, digits,
//                    '_', '-', ':', '.'. Cannot be empty.
//   label("name")    constructor. Accepts ANY non-empty string, including
//                    names with characters the dedicated syntax would reject.
//
// Show rules can target labels:
//   show <name>:        ...
//   show label("name"): ...
// Same effect; the second form lets you target dynamic / special-char names.

#show <a>: set text(fill: blue)
#show label("b.special:1"): set text(fill: red)

= Heading <a>

*Strong* #label("b.special:1")
