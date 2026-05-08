// 'emph(body)' TOGGLES italics:
//   normal      -> italic
//   italic      -> normal
//   oblique     -> normal
//
// Markup shorthand: enclose content in underscores '_..._'. The shorthand
// only applies at WORD BOUNDARIES. To emphasize PART of a word, you must
// call the function: 'extra#emph[ordinary]'.
//
// Show rules can target every emph element to restyle it globally.

This is _emphasized._ \
This is #emph[too.] \

Inside-word: extra#emph[ordin]ary

#show emph: it => text(fill: blue, it.body)

After the show rule, _this is blue + italic_ but not the surrounding text.

// Toggle: emph nested inside emph turns BACK to normal.
#emph[outer #emph[inner: not italic] outer again]
