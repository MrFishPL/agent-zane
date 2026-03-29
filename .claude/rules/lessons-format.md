# Lessons Format Specification

## Purpose

Lessons capture user feedback and domain insights so the agent improves over time. Each lesson generalizes specific feedback into a reusable rule.

## File Location

- Project-specific: `./lessons/YYYY-MM-DD_short-description.md`
- Global (all projects): `~/.claude/lessons/YYYY-MM-DD_short-description.md`

## Filename Format

`YYYY-MM-DD_short-description.md`

Examples:
- `2026-03-29_prefer-murata-for-mlcc.md`
- `2026-03-29_always-check-rohs-for-eu-projects.md`

## Required Fields

Every lesson file must contain this frontmatter and structure:

```markdown
---
title: Short descriptive title
date: YYYY-MM-DD
type: correction | preference | domain-insight
---

## Context
What was the user working on when this feedback was given.

## Feedback
The exact feedback or correction from the user.

## Generalized Rule
The reusable rule derived from this feedback. This is what the agent applies in future interactions.
```

## Field Descriptions

### type
- **correction**: User corrected a wrong recommendation (e.g., "That part is obsolete")
- **preference**: User expressed a preference (e.g., "I always use Wurth for inductors")
- **domain-insight**: User shared domain knowledge (e.g., "For audio, ceramic caps cause microphonics — use film")

## When to Create a Lesson

- User explicitly corrects a recommendation
- User states a preference ("I prefer X", "always use Y", "never suggest Z")
- User shares domain knowledge not obvious from datasheets
- User asks you to remember something

## When NOT to Create a Lesson

- One-off project-specific requests ("use this exact part for this one design")
- Information already in component datasheets
- Temporary constraints ("DigiKey is down today, use Mouser")

## How to Generalize

Turn specific feedback into broadly applicable rules:

- Specific: "Don't use TDK C series for this audio preamp"
- Generalized: "For audio circuits, avoid MLCC ceramic capacitors in signal path due to microphonic effects. Prefer film capacitors (e.g., Panasonic ECH-U, WIMA)."

## Example Lesson File

```markdown
---
title: Avoid MLCC in audio signal paths
date: 2026-03-29
type: domain-insight
---

## Context
User was designing an audio mixer preamp stage. Agent recommended a standard X7R MLCC for coupling capacitors.

## Feedback
"Ceramic caps cause microphonics in audio circuits. Use film caps for anything in the signal path."

## Generalized Rule
For audio signal path applications (coupling, filtering, feedback networks), do not recommend MLCC ceramic capacitors. Use film capacitors instead (polypropylene or polyester). MLCC is acceptable for power supply decoupling in audio circuits.
```
