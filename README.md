# AI020 — Municipal Meeting Summarizer

**AISO x AI020 Gov Tech Mini-Hackathon**
KIT Amsterdam · April 16, 2026 · 10:55 – 15:55

---

## The Problem

Raadsvergadering (council meeting) minutes are public, but inaccessible. Sessions run 3–5 hours, written in bureaucratic Dutch, and most residents have no idea what decisions are being made that affect their neighbourhood.

## The Challenge

Build a comprehensive tool that makes Dutch council meetings accessible to residents. Not just a summary — a product that a gemeente or neighbourhood could actually use.

This means thinking about the full picture: how the document gets in, how the AI processes it, how the output is presented, and how a user actually interacts with it.

## Repo Structure

```
brief/          → Problem statement, sample transcript, expected output
skills/         → Context files: Dutch gov structure, plain-language guidelines, output schema
CLAUDE.md       → Agent brief for Claude Code
AGENTS.md       → Agent brief for Codex
.cursorrules    → Agent brief for Cursor
```

## Getting Started

### 1. Pick your approach

| Level | Approach |
|-------|----------|
| **Non-technical** | Open this repo in Claude Code. Point it at the brief. Describe what you want in plain language — the AI writes all the code. You iterate by giving feedback. |
| **Mixed** | Let the AI generate a first version, then read and modify the code yourself. Adjust the output schema, refine the prompt, improve the UI. |
| **Technical** | Design the architecture yourself. Use the brief and skills files as context. AI assists, but you drive the implementation. |

### 2. Read the brief

Start with [`brief/problem.md`](brief/problem.md) — it has the full problem statement, constraints, and hints.

### 3. Try the sample transcript

Use [`brief/sample-transcript.txt`](brief/sample-transcript.txt) to test your solution. Compare your output against [`brief/expected-output.md`](brief/expected-output.md).

### 4. Use the skills files as context

Drop the files from `skills/` into your AI tool's context. They contain domain knowledge about Dutch government structure, plain-language writing guidelines, and a suggested output schema.

## Judging Criteria

- **Does it work?** Can you demo it with the sample document?
- **Is the output useful?** Would a resident or civil servant find real value in this?
- **How did you direct the AI?** Show your prompt — was it clear, specific, well-structured?
- **Pitch:** Can you explain the problem and your solution in 2 minutes?

## Timeline

| Time | Activity |
|------|----------|
| 10:55 – 11:15 | Intro + team formation. Briefs distributed. Repo cloned. |
| 11:15 – 14:45 | Build. Develop your prototype using AI coding tools. |
| 14:45 – 15:15 | Polish. Demo flow, edge cases, pitch prep. |
| 15:15 – 15:55 | Demos + judging. Each team presents for 3 minutes. |
