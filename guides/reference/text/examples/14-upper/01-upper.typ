// 'upper(text)' converts a STRING or CONTENT to uppercase. Mirror image
// of 'lower'.
//
// Notable mapping: German 'ß' -> "SS" (full case folding for the sharp s).

string input:    #upper("mixed Case String") \
content input:   #upper[*bold was preserved*] \
already upper:   #upper[ALREADY HIGH] \
'ß' -> "SS":     #upper("straße") \
unicode (æ ø é): #upper("æ ø é") \

// Common pattern: all-caps headings via show rule.
#show heading: it => upper(it.body)

= Lowercase in source becomes uppercase here

== Sub heading also gets upcased
