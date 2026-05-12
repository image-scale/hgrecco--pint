# Acceptance Criteria

## Tasks 1-5: Previous tasks
(completed)

## Task 6: Dimensionality analysis features

### Acceptance Criteria
- [ ] is_compatible_with() method checks if two quantities share the same dimensionality
- [ ] Q(1, "meter").is_compatible_with(Q(1, "kilometer")) returns True
- [ ] Q(1, "meter").is_compatible_with(Q(1, "second")) returns False
- [ ] to_compact() converts to a unit with a prefix that minimizes the magnitude: Q(0.001, "meter").to_compact() ≈ Q(1, "millimeter")
- [ ] to_compact() on Q(1500, "meter") gives something like Q(1.5, "kilometer")
- [ ] A @check decorator validates function argument dimensionality at call time
- [ ] @check('[length]', '[time]') on a function raises error if called with wrong dimensions
- [ ] compatible_units() returns a set of unit names sharing the same dimensionality
- [ ] Q(1, "meter").compatible_units includes "kilometer", "centimeter", etc.
- [ ] The registry's get_compatible_units("[length]") returns all length units
