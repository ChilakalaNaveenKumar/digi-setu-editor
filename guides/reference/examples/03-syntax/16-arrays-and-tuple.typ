// Demonstrates: array literals.
// Multi-element: (a, b, c). Empty: (). Single-element MUST have a trailing
// comma to disambiguate from a parenthesised expression: (a,).
// Without the comma, '(42)' is just the integer 42 in parentheses.

#let regions = ("us-east", "eu-west", "ap-south")
#let single-region = ("us-east",)   // trailing comma -> array of one
#let just-paren = (42)              // <-- this is the int 42, NOT an array

Regions: #regions.len() entries.
Single-element array length: #single-region.len()
Plain int (not array): #just-paren

First region: #regions.at(0)
Last region: #regions.last()
