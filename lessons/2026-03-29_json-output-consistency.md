---
title: JSON output schema must be structurally consistent
date: 2026-03-29
type: correction
---

## Context
Agent produced JSON recommendations where optional fields appeared inconsistently — some components had `datasheet_url` and `alternatives`, others omitted them entirely. The `message` field contained markdown formatting. Clarification questions included an undocumented `why` field.

## Feedback
"JSON schemas drift between tasks. Pick one approach and be consistent — either always include the field or never include empty fields. Don't mix. Don't use markdown inside JSON strings."

## Generalized Rule
Every JSON response must be structurally identical for its status type:
- Optional fields: always include them. Use `null` for unavailable strings, `[]` for unavailable arrays. Never omit an optional field from some components and include it in others within the same response.
- `message` field: plain text only. No markdown formatting (**bold**, *italic*, `code`). Use CAPS or dashes for emphasis if needed.
- Any new field added to a response must be documented in output-format.md before use. No ad-hoc fields.
