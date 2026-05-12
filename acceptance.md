# Acceptance Criteria

## Task 1-3: Previous tasks
(completed)

## Task 4: Temperature and offset unit handling

### Acceptance Criteria
- [ ] 0°C converts to 273.15 K
- [ ] 100°C converts to 373.15 K
- [ ] 0°F converts to approximately 255.37 K
- [ ] 212°F converts to 373.15 K (boiling point of water)
- [ ] 32°F converts to 273.15 K (freezing point of water)
- [ ] 100°C converts to 212°F
- [ ] 0°C converts to 32°F
- [ ] 0 K converts to -273.15°C
- [ ] Round-trip conversion: C → K → C preserves value
- [ ] Round-trip conversion: F → C → F preserves value
- [ ] Delta temperature units exist: delta_degC, delta_degF
- [ ] 1 delta_degC equals 1 K (same magnitude, no offset)
- [ ] 1 delta_degF equals 5/9 K
- [ ] Temperature differences (delta) can be added to absolute temperatures
- [ ] Rankine conversions work: 0°R equals 0 K
- [ ] 491.67°R equals 273.15 K (freezing point)
