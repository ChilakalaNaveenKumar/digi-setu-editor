// Versions support full ordering: ==  !=  <  <=  >  >=
// Comparison is component-wise (lexicographic), with implicit zeros for
// missing components.
//
// The compiler version is 'sys.version'. The standard pattern for
// version-gated polyfills is:
//
//   #if sys.version >= version(0, 13, 0) [
//     // new behavior
//   ] else [
//     // legacy behavior
//   ]

current sys.version:        #sys.version
sys.version >= 0.13.0:      #(sys.version >= version(0, 13, 0))
sys.version >= 99.0.0:      #(sys.version >= version(99, 0, 0))

3.2.0 > 4.1.0:              #(version(3, 2, 0) > version(4, 1, 0))
1.0   < 1.0.1:              #(version(1, 0)    < version(1, 0, 1))
1.0   == 1.0.0:             #(version(1, 0)    == version(1, 0, 0))

// Convert to a plain int array for iteration / further work.
sys.version as array:       #array(sys.version)
