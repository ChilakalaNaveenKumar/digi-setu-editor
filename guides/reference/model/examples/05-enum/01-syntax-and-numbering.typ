// 'enum' (NUMBERED LIST):
//
// MARKUP SHORTHAND:
//   '+' followed by a space        -> auto-numbered item
//   'N.' (digit + dot + space)     -> explicitly-numbered item
//
// Most-used fields:
//   numbering    str | function    pattern (default "1.")
//   start        auto | int        first number (default auto = 1)
//   full         bool              show parent numbers in nested items
//   reversed     bool              count down
//   tight        markup-driven (same as 'list')

= Auto-numbered

+ Preparations
+ Analysis
+ Conclusions

= Manually numbered

2. What is the first step?
5. I am confused.
+  Moving on ...

= Custom pattern

#set enum(numbering: "1.a)")

+ Different
+ Numbering
  + Nested
  + Items
+ Style

= Function pattern

#set enum(numbering: n => super[#n])

+ Superscript
+ Numbering!

= Start from a non-default value

#enum(start: 3, [Skipping], [Ahead], [Already at 5])

= Reversed counting

#set enum(numbering: "1.")
#enum(reversed: true, [Coffee], [Tea], [Milk])
