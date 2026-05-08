// Methods on 'int' (called as 'value.method(...)'):
//   .signum()              -> -1, 0, or +1
//   .bit-not()             -> bitwise NOT (treats value as signed 64-bit)
//   .bit-and(rhs)          -> bitwise AND
//   .bit-or(rhs)           -> bitwise OR
//   .bit-xor(rhs)          -> bitwise XOR
//   .bit-lshift(shift)     -> left shift; errors if it would overflow 64 bits
//   .bit-rshift(shift)     -> ARITHMETIC right shift (sign-extends).
//                              Pass 'logical: true' for an UNSIGNED right shift.
//
// Note: when calling a method on a numeric LITERAL with a leading '-' you
// must wrap it in parens: '(-5).signum()' (not '-5.signum()').

(5).signum():                  #(5).signum()
(-5).signum():                 #(-5).signum()
(0).signum():                  #(0).signum()

(4).bit-not():                 #(4).bit-not()
(-1).bit-not():                #(-1).bit-not()

128.bit-and(192):              #128.bit-and(192)
64.bit-or(32):                 #64.bit-or(32)
64.bit-xor(96):                #64.bit-xor(96)

33.bit-lshift(2):              #33.bit-lshift(2)
(-1).bit-lshift(3):            #(-1).bit-lshift(3)

64.bit-rshift(2):              #64.bit-rshift(2)
(-8).bit-rshift(2):            #(-8).bit-rshift(2)
(-8).bit-rshift(2, logical: true): #(-8).bit-rshift(2, logical: true)
