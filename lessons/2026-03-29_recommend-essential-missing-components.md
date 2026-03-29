---
title: Recommend essential components even if not on schematic
date: 2026-03-29
type: domain-insight
---

## Context
For an LM317 lab power supply, the agent added a filter capacitor after the bridge rectifier, a protection diode D2 (per datasheet design recommendations), and a heatsink — none of which were explicitly shown in the referenced schematic figure. Each addition was justified with a clear technical reason.

## Feedback
"Adding components not on schematic but necessary with clear justification — this is what the agent should do."

## Generalized Rule
For power supply and regulator circuits, always recommend essential components even if not explicitly shown on the schematic:
- Input filter/bulk capacitors after rectifier stages
- Protection diodes recommended by the regulator datasheet
- Heatsinks for linear regulators (with thermal justification)
- Snubber circuits for switching regulators if EMI is a concern
- Fuses or current limiting for mains-connected circuits

For other circuit types, apply the same principle: if a component is essential for safe/reliable operation and is standard practice per datasheet or application notes, include it. Always mark added components clearly (e.g., "not on schematic, added per datasheet recommendation") so the user knows what was added and why.
