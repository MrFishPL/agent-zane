---
title: Flag uncertain or potentially fabricated MPNs explicitly
date: 2026-03-29
type: correction
---

## Context
Agent recommended potentiometer MPN "RD901F-40-15R1-A1M" (Alpha). User questioned whether this is a real part number — it looked like it could be fabricated from a pattern rather than an actual catalog MPN.

## Feedback
"Are you confident this is a real part number? It looks like it could be fabricated. Flag uncertain MPNs explicitly."

## Generalized Rule
When recommending a component, explicitly state confidence level for each MPN:
- **Confirmed**: MPN was returned by an API or found on a distributor website via web search
- **Likely**: MPN follows a known manufacturer naming convention but was not directly verified
- **Uncertain**: MPN was constructed from a pattern — may not exist as listed

Never present an uncertain MPN as if it's confirmed. If you constructed an MPN from a naming pattern (e.g., guessing the suffix code for resistance value), say so: "MPN constructed from naming convention — verify at [distributor]." This is especially critical for parts with complex MPN encoding like potentiometers, connectors, and ICs with many variants.
