// 'alignment' is a TYPE that represents a position along an axis.
//
// Available values (globally + as alignment.<name>):
//   start     end                       (logical, follow text direction)
//   left      right                     (horizontal absolute)
//   top       bottom                    (vertical absolute)
//   center                              (horizontal middle)
//   horizon                             (vertical middle)
//
// 2-D alignments are made by addition: 'top + right', 'center + horizon', etc.

= Equivalent forms

#align(center)[A]
#align(alignment.center)[B]
// Both work; usually you'll use the bare 'center' form.

= Field access on a 2-D alignment

x: #(top + right).x         (right) \
y: #(top + right).y         (top) \
left.x: #left.x             (left) \
left.y: #left.y             (none -- not a vertical alignment)

= 'axis()' tells you which axis a 1-D alignment belongs to

#left.axis() / #right.axis() / #center.axis()  -- horizontal \
#top.axis() / #bottom.axis() / #horizon.axis() -- vertical

= 'inv()' returns the opposite

#top.inv() == bottom \
#left.inv() == right \
#center.inv() == center \
(left + bottom).inv() == #(left + bottom).inv()
