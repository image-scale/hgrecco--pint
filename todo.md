# Todo

## Plan
Build pint from the user-facing core outward. Start with the central Quantity class that users interact with most, backed by a UnitRegistry and unit definition parser. Then layer on formatting, temperature/offset units, measurement uncertainty, and advanced features. Each task delivers complete, testable user-facing functionality.

## Tasks
- [x] Task 1: Implement a unit registry that loads unit definitions from a text file, parses prefixes/units/dimensions/constants, and can create Quantity objects with a numeric magnitude and units that support conversion between compatible units (e.g., kilometers to meters), dimensional analysis, and basic arithmetic (+, -, *, /, **). Also handles unit parsing from strings with compound expressions, prefix resolution, pluralization, aliases, and symbols.
- [x] Task 2: (merged into Task 1 — parsing was already complete)
- [x] Task 3: Implement rich formatting for quantities and units supporting multiple output styles: default representation, compact/abbreviated notation using symbols, and LaTeX-compatible math output for scientific documents
- [x] Task 4: Implement temperature and offset unit handling so that conversions between Celsius, Fahrenheit, Kelvin, and Rankine work correctly, including proper distinction between absolute temperature values and temperature differences (delta)
- [x] Task 5: Implement a Measurement class that combines a quantity with an uncertainty value, propagates uncertainty through arithmetic operations, and formats results with plus-minus notation
- [>] Task 6: Implement dimensionality analysis features including a method to check if two quantities or units have compatible dimensions, a method to convert to compact representation (e.g., 0.001 m becomes 1 mm), a dimensionality check decorator for functions, and methods to list all compatible units for a given quantity
- [ ] Task 7: Implement comprehensive error handling with specific exception types for incompatible unit conversions, undefined units, definition syntax errors, and unit redefinition, with informative error messages
- [ ] Task 8: Implement unit system and grouping features allowing users to define named collections of units (e.g., "imperial", "metric") and retrieve compatible units for a given dimensionality
- [ ] Task 9: Implement context-dependent conversions that allow normally incompatible units to be converted when a physical relationship applies (e.g., wavelength to frequency using the speed of light in a spectroscopy context)
