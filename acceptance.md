# Acceptance Criteria

## Task 1: Core unit registry, quantity arithmetic, and unit conversion
(completed — 23/23 criteria met)

## Task 3: Rich formatting for quantities and units

### Acceptance Criteria
- [ ] Default format (D) displays units with full names and spaces: "5.0 meter / second"
- [ ] Compact format (C) displays without spaces around operators: "5.0 meter/second"
- [ ] Pretty format (P) uses unicode superscripts and dot multiplication: "5.0 meter·second⁻¹"
- [ ] LaTeX format (L) wraps units in \frac{}{} and \mathrm{}: "5.0 \\frac{\\mathrm{meter}}{\\mathrm{second}}"
- [ ] HTML format (H) uses <sup> tags for exponents: "5.0 meter/second<sup>2</sup>"
- [ ] Abbreviated/short flag (~) displays unit symbols instead of names: "5.0 m / s"
- [ ] Format specifier can combine magnitude format with unit format: format(q, ".2fD") gives formatted magnitude
- [ ] Quantity __format__ accepts standard Python format spec plus Pint flags
- [ ] Unit __format__ outputs the formatted unit (no magnitude)
- [ ] Exponent of 1 is not displayed: "meter" not "meter ** 1"
- [ ] Negative exponents in ratio form show as denominator: "meter / second" not "meter * second ** -1"
- [ ] Dimensionless quantities format without unit suffix
- [ ] Pretty format uses unicode superscripts for powers: "meter²" for meter**2
