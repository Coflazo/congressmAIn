```markdown
# Design System Strategy: The Civil Archive

## 1. Overview & Creative North Star
The Creative North Star for this system is **"The Civil Archive."** This is a digital translation of Dutch civic heritage—marrying the authoritative, ink-heavy aesthetic of the *Amsterdam Stadsarchief* with the frictionless, utilitarian focus of Apple Notes.

We are moving away from the "Software as a Service" (SaaS) aesthetic. There are no vibrant gradients, no heavy drop-shadows, and no rounded "pill" buttons. Instead, we embrace **Editorial Authority**. The UI should feel like a high-end government document: restrained, intentional, and permanent. We break the "template" look through generous whitespace, precise hairline strokes, and a stark contrast between sharp serif display type and functional sans-serif utility type.

## 2. Colors & Surface Expression
The palette is derived from Sanzo Wada’s historical color studies, favoring warm, organic tones over sterile digital grays.

### Surface Hierarchy & Nesting
Depth is not achieved through light and shadow, but through **Tonal Layering**. We treat the screen as a desk where sheets of archival paper are organized.
- **Base Layer:** Use `background` (`#FCF9F2`) for the main canvas.
- **Sectioning:** Use `surface_container_low` (`#F6F3EC`) to define large regions like sidebars or secondary panels.
- **Primary Content:** Use `surface` (`#FCF9F2`) or `surface_container_lowest` (`#FFFFFF`) for the main reading area to ensure maximum contrast for the `on_surface` (ink) text.

### The "No-Line" Rule (and the Hairline Exception)
Standard 1px borders often clutter a design. In this system:
1. **Primary separation** must be achieved via background color shifts (e.g., a `surface_container` card sitting on a `background` page).
2. **The Hairline Exception:** Use `outline_variant` (`#DFBFBC` at 20% opacity) or the `--line` token (`#E3DFD5`) strictly for "archival" definition—separating headers or creating table-like structures that feel like a physical ledger.

### Signature Textures
While we avoid corporate gradients, use a subtle **Tonal Wash** for primary CTAs. Instead of a flat hex code, a nearly imperceptible transition from `primary` (`#831517`) to `primary_container` (`#A42E2B`) gives buttons a "stamped ink" quality rather than a plastic feel.

## 3. Typography
Typography is our primary tool for hierarchy. We use a dual-typeface system to balance heritage with modern AI utility.

*   **Display & Headlines (GT Sectra):** These are our "Editorial" voice. Used for meeting titles and major section headers. Set these with **tight tracking (-2%)** to mimic the look of traditional typesetting.
*   **Body (Inter):** Our "Functional" voice. Set at 16px with a generous **1.6 line-height**. This ensures that long government summaries remain legible during high-stress reviews.
*   **Data & Meta (JetBrains Mono):** Use for timestamps, AI confidence scores, and technical metadata. This signals the "AI" aspect of the tool without breaking the archival aesthetic.

## 4. Elevation & Depth
We reject the 3D-lighting model of modern OS design. Hierarchy is conveyed through **Physicality**.

*   **The Layering Principle:** To lift an element, do not use a shadow. Instead, change the surface tier. A floating popover should use `surface_container_highest` (`#E5E2DB`) to appear "closer" to the eye than the paper below it.
*   **Ambient Shadows:** If a floating element (like a context menu) risks blending into the background, use a "Tinted Glow" instead of a shadow. Use `on_surface` at 5% opacity with a 32px blur—no offset. It should look like an ambient occlusion effect, not a light source.
*   **The Glassmorphism Rule:** For the 64px fixed topbar, use `surface` with a 90% opacity and a `backdrop-filter: blur(10px)`. This allows the "paper" of the document to scroll underneath, maintaining a sense of place.

## 5. Components

### Buttons
- **Primary:** `primary` background, `on_primary` text. 4px radius. No shadow.
- **Secondary:** 1px hairline border using `outline`. No background.
- **Interaction:** On hover, shift the background to `primary_container`. Transitions should be immediate (150ms) to feel "mechanical."

### Cards & Summaries
- **Constraint:** Forbid divider lines within cards.
- **Structure:** Use `surface_container_low` for the card body. Use vertical whitespace (16px, 24px, 32px) to separate the summary title from the body text.
- **Radius:** Strictly 6px. This provides just enough softness to feel modern without becoming "bubbly."

### Input Fields
- **Aesthetic:** Minimalist "Form" style. A bottom-only border using `outline_variant`.
- **Focus State:** The border transitions to `primary` (Amsterdam Red) with a 1px thickness. Helper text should always be in `label-sm` (Inter).

### Archival Chips
- Use `secondary_container` (`#ECE0B4`) for tags or categories.
- No border, 2px radius (near-square). These should look like small physical tabs used in a filing system.

### The "AI Indicator"
- Since this is an AI summarizer, use a subtle `highlight` (`#F0E4B8`) background for AI-generated text blocks to differentiate them from human-edited notes, mimicking an archival highlighter.

## 6. Do's and Don'ts

### Do
- **Use Asymmetry:** Allow the main content (1200px max) to sit slightly off-center or use wide left margins for "marginalia" (metadata/tags).
- **Embrace the Paper:** Use `#F4F1EA` as your default mental "white." Pure white (`#FFFFFF`) should be reserved only for the highest-level "sheets" of content.
- **Respect the Grid:** While we avoid boxes, the alignment of text must be mathematically perfect. Use 8px increments for all spacing.

### Don't
- **No Heavy Shadows:** Shadows are a sign of "default" UI. Use tonal shifts instead.
- **No Rounded Ends:** Never use a radius larger than 6px. We are building a civic tool, not a social media app.
- **No High-Contrast Borders:** A 100% black border is too aggressive. Always use the `line` or `outline_variant` tokens for a softer, historical feel.
- **No Motion Blur:** Keep UI animations snappy and linear. Elements should "appear" or "slide" as if being placed on a table.```