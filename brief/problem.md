# Challenge: Municipal Meeting Summarizer

## The Problem

Every Dutch municipality holds regular council meetings (raadsvergaderingen). These meetings are where local laws are passed, budgets are approved, and decisions are made about housing, traffic, schools, and public services.

The transcripts are public — that's the law. But in practice, nobody reads them:

- Sessions run **3–5 hours**
- They're written in **bureaucratic Dutch** full of jargon
- There's **no summary, no highlight reel, no "here's what matters to you"**
- Residents have **no easy way** to find out what was decided about their neighbourhood

This means local democracy is technically transparent, but functionally opaque.

## What You're Building

A comprehensive tool that makes council meetings accessible to residents. Not just a summary — a product that someone at a gemeente or in a neighbourhood could actually use.

Think about the full picture:

### Getting the document in
- How does a user provide the transcript? Upload a PDF? Paste text? Link to a gemeente website?
- Can you handle messy real-world input — not just the clean sample?

### Understanding the content
- Extract decisions, votes, amendments, motions, and commitments (toezeggingen)
- Handle edge cases: failed motions, postponed items, procedural vs. substantive votes
- Preserve accuracy — never invent information that isn't in the transcript

### Presenting the output
- Make it browsable, not just a wall of text
- Can a resident quickly find what affects them?
- Think about: filtering by topic, searching by keyword, highlighting what's relevant to a specific neighbourhood
- Vote visualisations, timelines, decision tracking

### Making it trustworthy
- Can the reader trace a summary back to the original transcript?
- How do you show what the AI is confident about vs. where the transcript was ambiguous?

### Making it accessible
- Plain Dutch (B1 level) — understandable by someone who recently learned Dutch
- Multi-language output for a diverse city?
- Mobile-friendly for someone checking on their phone?

## The Sample

Use `sample-transcript.txt` to develop and test your solution. Compare your output against `expected-output.md` for a reference of what the core summary should capture.

But a good solution goes beyond the sample — think about what happens when you throw a real, messy, 50-page transcript at it.

## Skills / Context Files

The `skills/` folder contains domain knowledge you can feed to your AI tool:

- **`dutch-gov-structure.md`** — how Dutch municipal government works, roles, decision types, jargon
- **`plain-language.md`** — guidelines for writing plain Dutch summaries
- **`output-schema.json`** — a suggested structured output format (adapt it to your needs)

## Hints

- Start with the core: get the AI to produce useful, structured output from the sample transcript. Then build outward.
- Think about who the user is. A resident who has 2 minutes and wants to know "did anything happen that affects me?" A journalist tracking how parties vote. A civil servant preparing a briefing.
- The best solutions will feel like a product, not a demo.
