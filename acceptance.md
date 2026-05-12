# Acceptance Criteria

## Tasks 1-4: Previous tasks
(completed)

## Task 5: Measurement class with uncertainty

### Acceptance Criteria
- [ ] Measurement can be created from a value quantity and an error quantity: Measurement(4.0, 0.1, "s")
- [ ] Measurement exposes .value (as Quantity), .error (as Quantity), and .rel (relative error)
- [ ] Measurement can be created from two Quantities: Measurement(Q(4, "s"), Q(0.1, "s"))
- [ ] Measurement addition propagates error: sqrt(err1^2 + err2^2)
- [ ] Measurement subtraction propagates error: sqrt(err1^2 + err2^2)
- [ ] Measurement multiplication propagates relative error: sqrt(rel1^2 + rel2^2) * result
- [ ] Measurement division propagates relative error: sqrt(rel1^2 + rel2^2) * result
- [ ] Measurement can be multiplied/divided by a scalar (error scales proportionally)
- [ ] str() formats as "value +/- error unit"
- [ ] Measurement can be converted to different units preserving the relative error
- [ ] Measurement has .magnitude and .units properties matching the value
