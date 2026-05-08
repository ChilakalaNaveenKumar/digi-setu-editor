// 'lower(text)' converts a STRING or CONTENT to lowercase.
//
// Return type matches input:
//   lower("ABC")      -> "abc"               (str)
//   lower([*BIG*])     -> [*big*]              (content; formatting preserved)
//
// Uses Unicode-correct casing -- handles ß -> ss is NOT done here (that's
// special), but most multi-codepoint case mappings work.

string input:    #lower("MIXED Case String")  \
content input:   #lower[*BOLD WAS PRESERVED*] \
already lower:   #lower[already low]            \
unicode (ä Ñ ß): #lower("ÄÑß")                  \

// Use in pipelines / show rules:
#show heading: it => upper(it.body) + parbreak() + lower(it.body)

= My Section
