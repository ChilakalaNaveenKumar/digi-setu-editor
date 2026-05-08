// String LITERALS use double quotes. Escape sequences (same as the markup):
//   \\         backslash
//   \"         double quote
//   \n         newline
//   \r         carriage return
//   \t         tab
//   \u{1f600}  Unicode codepoint by hex
//
// All other characters are literal. There is NO single-quote string literal.
// For multi-line / no-escape needs, use a RAW BLOCK and grab '.text':
//   `multi
//   line`.text
//
// 'str(value, base: int = 10)' converts to string. Accepts: int, float,
// str, bytes, label, decimal, version, type. Notes:
//   - integers default to base 10; 'base:' (2..36) overrides
//   - floats are decimal, NEVER scientific  (1e8 -> "100000000")
//   - negatives use Unicode minus '\u{2212}', not ASCII '-'
//   - bytes decode as UTF-8
//   - labels yield their name (no '<>')

literal:           #"hello world!"
escaped:           #"\"q\"\n  \\bs\u{1f600}"
raw-block as str:  #`one
two`.text

str(10):           #str(10)
str(4000, 16):     #str(4000, base: 16)
str(2.7):          #str(2.7)
str(1e8):          #str(1e8)
str(-1.5):         #str(-1.5)
str(<intro>):      #str(<intro>)
str(decimal):      #str(decimal("3.140"))
str(bytes "Hi!"):  #str(bytes("Hi!"))
str(version):      #str(version(0, 14, 2))
str(int type):     #str(int)
