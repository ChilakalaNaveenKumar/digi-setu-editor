// Demonstrates: dot notation for FIELD access and METHOD calls.
//   value.field          value at a key/property (dictionary, content, ...)
//   value.method(args)   call a function scoped to value's type
// Method form is sugar:  "abc".len()  ==  str.len("abc").

#let cfg = (region: "us-east", retries: 3)
Region field: #cfg.region

#let regions = ("us-east", "eu-west", "ap-south")
Method call: #regions.len() regions, joined: #regions.join(", ")

// Method chaining
#let csv-line = "build,1407,green"
#let parts = csv-line.split(",")
First column: #parts.first(), last column: #parts.last().
