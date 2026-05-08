// 'cite(key: label, supplement: ?, form: "normal"|"prose"|"full"|"author"|"year"|none, style: ?)'
// references a work in the bibliography.
//
// You almost always use the @key syntax (same shorthand as 'ref'). Reach for
// '#cite(...)' explicitly when:
//   - you need a non-default 'form' or 'style' for ONE citation
//   - the key contains characters '@' can't parse (then use 'label("...")')

#bibliography("_assets/works.bib", style: "apa")

= Default form: end-of-sentence citation

This was already noted by pirates long ago. @arrgh

Multiple sources back this up: @arrgh @netwok.

Calling cite explicitly: #cite(<arrgh>).

Bibliography keys with special characters require label():
#cite(label("netwok")).

= 'prose' form: inside the sentence flow

#cite(<netwok>, form: "prose") show the outsized effects of pirate life on
the human psyche.

= 'author' and 'year' forms

Just the author: #cite(<distress>, form: "author"). \
Just the year:   #cite(<distress>, form: "year"). \
Together:        #cite(<distress>, form: "author") (#cite(<distress>, form: "year")).

= Supplement (page / chapter info)

This has been proven. @distress[p.~7]

Equivalent explicit form: #cite(<distress>, supplement: [p.~7]).

= 'form: none' silently registers a citation

Behind the scenes: #cite(<tolkien54>, form: none). The work is now in the
bibliography even though nothing was printed here.
