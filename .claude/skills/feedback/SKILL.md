---
name: feedback
description: Save user feedback as a lesson for future sessions. Use /feedback after receiving component recommendations to correct, express preferences, or share domain insights. The agent saves structured lessons to lessons/ directory.
allowed-tools: Read, Write, Glob, Grep
user-invocable: true
---

The user is providing feedback on a recent recommendation. Save it as a lesson.

## Process

1. **Parse the feedback** — identify what the user is saying:
   - **Correction**: "That part is wrong/obsolete/too expensive" → type: correction
   - **Preference**: "I always use X", "prefer Y over Z" → type: preference
   - **Domain insight**: "For audio, never use MLCC in signal path" → type: domain-insight

2. **Generalize** — turn the specific feedback into a reusable rule:
   - Don't just record "don't use TDK C series for this preamp"
   - Generalize to: "For audio signal paths, avoid MLCC ceramics due to microphonics. Use film capacitors."

3. **Write the lesson file** to `lessons/` following the format in `.claude/rules/lessons-format.md`:
   - Filename: `YYYY-MM-DD_short-description.md`
   - Frontmatter: title, date, type
   - Sections: Context, Feedback, Generalized Rule

4. **Confirm** — tell the user what was saved and how it will be applied in future sessions. Keep it brief.

## Rules

- One lesson per distinct piece of feedback. If the user gives 3 separate points, create 3 files.
- Check existing lessons first (read `lessons/` directory) — if feedback updates an existing lesson, edit that file instead of creating a duplicate.
- Never create a lesson for one-off requests or temporary constraints.
- Today's date is used for the filename and date field.
