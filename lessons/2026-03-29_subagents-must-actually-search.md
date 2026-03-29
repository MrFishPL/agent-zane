---
title: Component sourcer subagents must use web search tools — never answer from training data alone
date: 2026-03-29
type: correction
---

## Context
Agent spawned 3 component-sourcer agents (DigiKey, Mouser, LCSC) in parallel. LCSC agent made 56 tool calls and actually searched the web. DigiKey and Mouser agents made 0 tool calls — they fabricated answers entirely from training data without searching anything.

## Feedback
User caught the discrepancy from the tool usage stats. "Only LCSC actually searched — DigiKey and Mouser agents just made up answers from training data. This is a critical problem."

## Generalized Rule
Every component-sourcer agent MUST use WebSearch and/or WebFetch tools to look up real data. If a sourcer agent returns results with 0 tool calls, its output is fabricated and must be flagged as FABRICATED (not just UNVERIFIED). The distinction matters:
- **UNVERIFIED**: data came from a web search but not an official API — may be stale
- **FABRICATED**: data came from training knowledge with no search performed — may be completely wrong

When presenting results, report tool usage per agent so the user can assess confidence. If an agent didn't search, say so explicitly.
