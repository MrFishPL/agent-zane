---
title: Verify component values against circuit topology
date: 2026-03-29
type: domain-insight
---

## Context
When sourcing components for an audio mixer, the agent caught that user-specified 1M potentiometers were incompatible with the circuit topology (which needed 10k-50k for proper impedance matching).

## Feedback
"This kind of domain expertise check is exactly what the agent should do."

## Generalized Rule
Always verify that user-specified component values are compatible with the circuit topology before sourcing. Specific checks:
- Potentiometer impedance vs. circuit impedance (source/load matching)
- Capacitor values vs. required cutoff frequencies
- Resistor values vs. expected current/voltage levels
- Voltage ratings vs. actual circuit voltages (with derating)

If a user-specified value is incompatible, flag it with an explanation of why it won't work and suggest the correct range. Don't silently substitute.
