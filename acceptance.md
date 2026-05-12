# Acceptance Criteria

## Tasks 1-6: Previous tasks
(completed)

## Task 7: Comprehensive error handling

### Acceptance Criteria
- [ ] All error classes support pickling via __reduce__
- [ ] IncompatibleDimensionError includes units and dimensions in its message
- [ ] UnitNotFoundError includes the unknown unit name in its message
- [ ] DefinitionParsingError includes the offending line in its message
- [ ] DuplicateDefinitionError includes the name and type in its message
- [ ] OffsetUnitError includes the involved units in its message
- [ ] Converting incompatible units raises IncompatibleDimensionError
- [ ] Looking up undefined units raises UnitNotFoundError
- [ ] Adding meters + seconds raises IncompatibleDimensionError
- [ ] float() on a non-dimensionless quantity raises IncompatibleDimensionError
- [ ] Errors can be caught by both their specific type and PintError base class

## Task 8: Unit systems and groups

### Acceptance Criteria
- [ ] Groups can be defined in definition files with @group ... @end syntax
- [ ] Groups contain a set of unit names; get_group(name).members returns them
- [ ] Groups can include other groups via "using" keyword
- [ ] Systems can be defined in definition files with @system ... @end syntax
- [ ] Systems specify base unit replacements (e.g., use "yard" instead of "meter")
- [ ] ureg.sys.system_name returns the System object
- [ ] get_compatible_units can filter by group or system name
- [ ] get_base_units returns results in the system's preferred base units

## Task 9: Context-dependent conversions

### Acceptance Criteria
- [ ] Contexts can be defined in definition files with @context ... @end syntax
- [ ] Contexts support parameters with defaults: @context(n=1) spectroscopy
- [ ] Inside a context, normally incompatible conversions work via dimension rules
- [ ] with ureg.context("spectroscopy"): wavelength.to("Hz") succeeds
- [ ] Without a context, the same conversion raises IncompatibleDimensionError
- [ ] Bidirectional rules (<->) work in both directions
- [ ] Unidirectional rules (->) only work in the specified direction
- [ ] Context parameters can be overridden: ureg.context("spectroscopy", n=2)
