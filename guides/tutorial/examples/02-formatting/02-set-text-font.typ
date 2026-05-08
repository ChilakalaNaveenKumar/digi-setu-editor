// Demonstrates: 'set' rule. Sets default values for parameters of a function
// for every subsequent invocation of that function in the enclosing scope.
// '#set text(font: ...)' applies to every text element from this point on.

#set text(font: "Libertinus Serif")

= Quarterly Report
This entire document now renders in Libertinus Serif.
The set rule does not need to wrap the content; it is
declarative and applies forward in scope.
