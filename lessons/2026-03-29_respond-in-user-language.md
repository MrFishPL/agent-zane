---
title: Respond in the user's language
date: 2026-03-29
type: preference
---

## Context
User wrote requests in Polish. Agent responded with Polish-language message fields in JSON and Polish descriptions. User confirmed this was the right behavior.

## Feedback
"Responding in the user's language — save as a rule."

## Generalized Rule
Always match the language of the response to the language the user writes in. If the user writes in Polish, respond in Polish (including the `message` field in JSON and component descriptions). If in English, respond in English. Do not mix languages within a single response. Technical terms (MPN, package names, standard abbreviations) may remain in English as they are universal.
