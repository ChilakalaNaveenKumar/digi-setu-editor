// 'ratio' is a TYPE for percentages (0%, 25%, 100%, ...).
// They appear most commonly as part of a 'relative' length, but can
// also describe non-length quantities (scaling factors, parens height).

= As a length component

#rect(width: 25%)             // 25% of container width
#rect(width: 25% + 1cm)        // 25% + 1cm

= Multiplication

#(27% * 10%)              // 2.7%   (ratio  * ratio  -> ratio)
#(27% * 100pt)            // 27pt   (ratio  * length -> length)
#(27% * 100deg)           // 27deg  (ratio  * angle  -> angle)
#(27% * 2)                // 54%    (ratio  * int    -> ratio)
#(27% * 0.37037)          // 10%    (ratio  * float  -> ratio)
#(27% * 3fr)              // 0.81fr (ratio  * fr     -> fr)

= As a non-length quantity

#scale(x: 75%)[scaled]                // x scale factor as a ratio
$ lr( |a/b|, size: #50% ) $          // delim height = 50% of content
