// 'binom(upper, ..lower)' renders a binomial / multinomial coefficient.
//
// Multiple lower indices become a multinomial coefficient with commas
// between them.

= Standard binomial

$ binom(n, k) = (n!) / (k! (n - k)!) $

= Multinomial coefficient

$ binom(n, k_1, k_2, k_3, ..., k_m) $

= Inside an expression

$ (1 + x)^n = sum_(k=0)^n binom(n, k) x^k $
