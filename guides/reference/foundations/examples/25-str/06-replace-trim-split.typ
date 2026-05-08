// .replace(pat, replacement, count: int) -> str
//   replacement may be a string OR a function. The function form receives
//   the same match-dict shape as '.match' and returns a string per call.
//   'count:' caps the number of replacements (default = unlimited).
//
// .trim(pat = none, at: alignment, repeat: bool) -> str
//   pat = none means trim Unicode whitespace.
//   at:  start | end  to trim only one side; omit to trim both.
//   repeat: true (default) keeps trimming as long as the pattern matches.
//
// .split(pat = none) -> array<str>
//   pat = none splits on RUNS of whitespace (and drops leading/trailing empties).
//   pat = "" puts an empty string between every codepoint AND at the ends.

basic replace:
  #"score: 100 / total: 250".replace(regex("\d+"), "?")

capped replace (count: 1):
  #"a a a".replace("a", "b", count: 1)

function replacement:
  #"name=Alice; lang=en".replace(
    regex("(\w+)=(\w+)"),
    m => upper(m.captures.at(0)) + "=" + lower(m.captures.at(1)),
  )

trim ws both sides:
  #repr("  hello  ".trim())

trim '-' end only:
  #repr("---hello---".trim("-", at: end))

trim once (no repeat):
  #repr("---hello---".trim("-", repeat: false))

split on whitespace:
  #"  a  b   c ".split()

split on regex [,;]:
  #"x,y;z,w".split(regex("[,;]"))

split on empty string:
  #"abc".split("")
