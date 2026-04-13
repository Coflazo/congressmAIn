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

A tool that takes a council meeting transcript and produces a **structured, plain-language summary**.

For each agenda item, the summary should answer:

1. **What was discussed?** (topic, in one sentence)
2. **What was decided?** (the outcome)
3. **How did they vote?** (for/against/abstain, by party if available)
4. **What does this mean for residents?** (plain-language impact)

## Constraints

- **Language:** Output must be in plain Dutch, understandable at B1 level (think: someone who recently learned Dutch, or a busy parent skimming on their phone)
- **Accuracy:** Do not invent information. If the transcript doesn't mention a vote count, don't guess one.
- **Structure:** Use the output schema in `skills/output-schema.json` as a starting point — you can adapt it.
- **Completeness:** Cover all agenda items, not just the interesting ones.

## Input

A text transcript of a Dutch municipal council meeting. See `sample-transcript.txt` in this folder.

In a real product this could come from:
- PDF minutes published on gemeente websites
- Audio recordings transcribed with speech-to-text
- Live streams with real-time transcription

For this hackathon, you're working with text input.

## Output

A structured summary. See `expected-output.md` for an example of what good output looks like.

## Hints

- Start with the prompt. Get the LLM to produce useful output from the sample transcript before worrying about UI.
- The `skills/` folder has context files you can feed to the LLM — Dutch government structure, plain-language guidelines, and an output schema.
- Think about who the user is: a resident who has 2 minutes and wants to know "did anything happen that affects me?"
- Edge cases to consider: motions that fail, amendments, items that are postponed, procedural votes vs. substantive votes.
