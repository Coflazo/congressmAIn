# Google Stitch design prompt

Paste the prompt below into https://stitch.withgoogle.com/ to regenerate or iterate on the UI screens. Request one screen at a time for best results. The generated HTML files live in `design/`.

---

```
Design a single-page civic web application called "congressmAIn" — a Dutch government meeting summarizer. Philosophy: Amsterdam Stadsarchief meets Apple Notes. Restrained, editorial, highly legible. Zero gradients, zero SaaS chrome.

PALETTE (Sanzo Wada "Dictionary of Color Combinations" — combination #21 / #91 hybrid, dutch civic register):
--bg: #F4F1EA             (warm archival paper)
--surface: #FCFAF5
--ink: #1C1C18            (near-black, warm not cold)
--ink-muted: #58413F
--accent: #831517         (Amsterdam municipal red — deep, muted, authoritative)
--accent-soft: #E8D5D3
--line: #DFBFBC           (warm hairline border, 20% opacity)
--highlight: #F0E4B8      (soft ochre, PDF annotation yellow)
--success: #194B30
--secondary-container: #ECE0B4
--surface-container: #F1EEE7

TYPOGRAPHY:
- Headlines: "Newsreader" serif (fallback Georgia), tight tracking (-2%), 32/28/24/20px scale
- Body: "Inter" system-ui, 16px, 1.6 line-height
- Dates/IDs/numbers: "JetBrains Mono" 13px
- All text: var(--ink)

ICONS: Lucide stroke icons, 1.5px weight, 20px default. No emoji.

LOGO: Gemeente Amsterdam coat of arms (red shield, three X's). Height 28px in topbar. URL: https://upload.wikimedia.org/wikipedia/commons/thumb/4/4c/Logo_of_Gemeente_Amsterdam.svg/3840px-Logo_of_Gemeente_Amsterdam.svg.png

RULES:
- Fixed topbar 64px: logo + "congressmAIn" serif left, tabs centered, lang switcher (NL EN TR PL UK) + account right
- Max content width 1200px, 48px desktop gutters, 24px mobile gutters
- Hairline 1px borders in var(--line), NO drop shadows, NO blur
- Border radius: 6px cards, 4px buttons, 2px chips, 0px tables
- All interactive: 2px focus ring in var(--accent)
- Background is always var(--bg), never pure white

SCREEN 1 — Vergaderingen (default tab)
Left filter rail 240px (collapsible mobile): topic chips, date range picker, municipality select (Tweede Kamer / Gemeenteraad Amsterdam / Provinciale Staten). 
Main area: search bar at top. Below: editorial list of meeting cards (NOT a grid).
Each card: date in mono muted top-left, title in serif 20px, municipality in mono small, 2-line summary snippet in body, topic chips (secondary-container bg, 2px radius), "X sprekers · Y besluiten" in mono muted, right arrow.
Empty state: line illustration of folded paper document.
Mobile: filter moves to bottom sheet triggered by Filter button with count badge.

SCREEN 2 — Meeting Detail
Breadcrumb: Vergaderingen / [Meeting Title]
Meeting header: date mono, title serif large, municipality mono, download PDF ghost button.
Secondary tab strip: PDF · Samenvatting · Wie zei wat · Besluiten · Vraag AI

PDF tab: split view — PDF pane 60% left, controls + speaker list 40% right. Speaker names as chips (accent-soft bg when active). Active speaker's segments highlighted in ochre overlay on PDF.

Samenvatting tab: single column max-width 680px, language toggle top-right. "Kernpunten" callout box (secondary-container bg). Decisions as numbered cards with 3px border-left in var(--accent).

Wie zei wat tab: Speaker chips list (name + party badge). Click expands their quoted passages indented under chip. Each passage has mono page number and "Open in PDF →" link.

Besluiten tab: numbered list. Each item: title bold, status badge (aangenomen/verworpen/aangehouden — green/red/orange), vote counts in mono, resident impact paragraph.

Vraag AI tab: chat interface. Message bubbles (user right, assistant left in surface-container). AI answers have ochre (--highlight) tinted bg. Citation pills below AI answers (mono, accent border). Input fixed bottom, Send button primary.

SCREEN 3 — Abonnementen
Two-column desktop: form left, email preview right.
Form: email input (bottom-border only, no box), language select, topic multiselect as toggleable chips.
Email preview: mini scaled-down mockup of the digest email.
Primary Save button, full width mobile.
Below: current subscriptions as deletable chips.

SCREEN 4 — Over
Editorial long-form. Hero: product name serif large, one-sentence explainer.
4-step process (numbered circles 40px, thin connecting vertical line between them): Meeting → PDF → ai@gov.nl → Samenvatting → Lezer.
FAQ accordion, hairline dividers between items.
Footer: "Gebouwd met Claude · congressmAIn · Amsterdam 2025"

SCREEN 5 — Admin
4 stat cards top: meetings processed, active subscribers, digest success rate, avg processing time. All numbers in mono bold.
Two tabs below: Vergaderingen table, Abonnees table.
Table: hairline row dividers only. Status badge chips. Reprocess button ghost small on each failed row.
No card wrappers on tables — just the hairline.

SCREEN 6 — Email Digest (HTML render, 600px max-width)
Single column, table layout, inline styles.
Top: Amsterdam logo centered 48px.
Eyebrow: "congressmAIn briefing" mono muted small.
Meeting title serif large. Date + municipality mono.
Lead paragraph: plain-language summary opener.
3 decision cards: thin left border var(--accent), title bold, outcome chip, resident impact text.
CTA button: "Open op het platform" — accent bg, white text, 4px radius, 48px height.
"Stel een vraag" explainer text, italic serif.
Collapsible "Wie zei wat" as <details> tag.
Footer: unsubscribe link mono small, muted.

OUTPUT REQUIREMENTS:
Each screen as standalone HTML + embedded CSS (no frameworks). Use CSS custom properties for all tokens at :root. Include token list comment at top of each file. Self-contained assets (logos by URL). Export-ready for developer to convert to React + Tailwind.
```
