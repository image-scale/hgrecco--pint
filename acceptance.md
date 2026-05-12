# Acceptance Criteria

## Task 1: Core unit registry, quantity arithmetic, and unit conversion

### Acceptance Criteria
- [ ] A UnitRegistry can be created and loads unit definitions from a text file
- [ ] The registry parses prefix definitions (e.g., "kilo- = 1e3 = k-") and stores them
- [ ] The registry parses base unit definitions (e.g., "meter = [length] = m = metre") with dimensions, symbols, and aliases
- [ ] The registry parses derived unit definitions (e.g., "minute = 60 * second = min")
- [ ] The registry parses dimension definitions (e.g., "[area] = [length] ** 2")
- [ ] The registry parses constant definitions (e.g., "speed_of_light = 299792458 m/s = c")
- [ ] Quantity objects can be created with a magnitude and unit string (e.g., Quantity(5.0, "meter"))
- [ ] Quantity objects expose .magnitude and .units properties
- [ ] Quantities with compatible units can be added/subtracted (e.g., 1 km + 500 m = 1500 m)
- [ ] Adding quantities with incompatible units raises an error (e.g., 1 m + 1 s)
- [ ] Quantities can be multiplied and divided by scalars (e.g., 2 * Q(3, "m") = Q(6, "m"))
- [ ] Quantities can be multiplied/divided by each other (e.g., Q(10, "m") / Q(2, "s") yields m/s)
- [ ] Quantities can be raised to a power (e.g., Q(3, "m") ** 2 yields 9 m**2)
- [ ] Quantities can be converted to compatible units via .to() (e.g., Q(1, "km").to("m") == Q(1000, "m"))
- [ ] Converting to incompatible units raises an error (e.g., Q(1, "m").to("s"))
- [ ] Quantities can be converted to base units via .to_base_units()
- [ ] Quantity equality works across units (e.g., Q(1000, "mm") == Q(1, "m"))
- [ ] Quantities can be compared with <, >, <=, >= for same-dimension quantities
- [ ] Quantities can be converted to float/int for dimensionless quantities
- [ ] Quantities have a dimensionality property returning base dimensions
- [ ] The Unit class represents a unit without magnitude and supports unit algebra (*, /, **)
- [ ] str() on a Quantity produces a readable string like "5.0 meter"
- [ ] The registry handles @import directives to load additional definition files
