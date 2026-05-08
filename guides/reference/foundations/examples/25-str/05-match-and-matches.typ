// .match(pat)   -> dict | none   first match with details
// .matches(pat) -> array<dict>    all matches
//
// Each match dict has:
//   start     int   byte offset of match start
//   end       int   byte offset of match end (exclusive)
//   text      str   the matched substring
//   captures  array<str>   one entry per capturing group (NOT including
//                          the whole match). Empty unless 'pat' is a regex
//                          with capturing groups.

#let pat = regex("not (a|an) (apple|cat)")

match (with captures):
  #"I'm a doctor, not an apple.".match(pat)

no match (returns 'none', so check before using):
  #{
    let m = "plain text".match(pat)
    if m == none [(no match)] else [#m]
  }

#let times = "10:42, 11:07, 23:59"
all times:
  #times.matches(regex("(\d{1,2}):(\d{2})")).map(m => (
    text: m.text,
    h: m.captures.at(0),
    m: m.captures.at(1),
  ))
