# AI020 — Municipal Meeting Summarizer

**AISO x AI020 Civic Tech Mini-Hackathon**
KIT Amsterdam · April 16, 2026 · 3.5 hours

---

## The Problem

Raadsvergadering (council meeting) minutes are public, but inaccessible. Sessions run 3–5 hours, written in bureaucratic Dutch, and most residents have no idea what decisions are being made that affect their neighbourhood.

## The Challenge

Build a tool that takes a council meeting transcript and produces a clear, structured summary: what was decided, how people voted, and what it means for residents — in plain language.

**Input:** a transcript or PDF of a Dutch municipal council meeting
**Output:** decisions, votes, and plain-language resident impact

## Repo Structure

```
brief/          → Problem statement, sample transcript, expected output
skills/         → Context files: Dutch gov structure, plain-language guidelines, output schema
starter/        → A prompt template and a simple HTML page to get going
CLAUDE.md       → Agent brief for Claude Code
AGENTS.md       → Agent brief for Codex
.cursorrules    → Agent brief for Cursor
```

## Getting Started

### 1. Pick your approach

| Level | Approach |
|-------|----------|
| **Non-technical** | Open this repo in Claude Code. Use the brief and skills files to direct the AI. Iterate on the prompt and output. |
| **Mixed** | Start from the prompt template and HTML page in `starter/`. Modify the prompt, adjust the output schema, tweak the UI. |
| **Technical** | Start from scratch using only `brief/` and `skills/` as context. Full creative freedom. |

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
- **Pitch:** Can you explain the civic problem and your solution in 2 minutes?

## Timeline

| Time | Activity |
|------|----------|
| 0:00 – 0:20 | Intro + team formation. Briefs distributed. Repo cloned. |
| 0:20 – 2:30 | Build. Develop your prototype using AI coding tools. |
| 2:30 – 3:00 | Polish. Demo flow, edge cases, pitch prep. |
| 3:00 – 3:30 | Demos + judging. Each team presents for 3 minutes. |
