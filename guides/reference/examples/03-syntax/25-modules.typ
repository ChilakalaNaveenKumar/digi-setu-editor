// Demonstrates: importing items from a sibling Typst module.
// Forms (showing the most common):
//   #import "_helpers.typ"            // module bound as 'helpers' (filename stem)
//   #import "_helpers.typ": item, ... // selected items into local scope
//   #import "_helpers.typ": *         // everything (use sparingly)
//   #import "_helpers.typ" as alias   // rename the module binding
// 'include' (not used here) inlines a file's CONTENT instead of importing names.

#import "_helpers.typ": MODULE_TITLE, greet, banner

= #MODULE_TITLE

#banner("Build Report")
#greet("ops team")
