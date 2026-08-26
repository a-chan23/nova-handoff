# Executive story deck — "Quiet Signal" theme

`build_story_deck.js` regenerates `QA_Handoff_Story_Deck.pptx` (12 slides, 16:9 at
13.333 × 7.5in) from source. The original Google-Slides export is not needed — all of its
content, including speaker notes, lives in the generator.

```bash
npm install pptxgenjs          # once
node build_story_deck.js       # writes QA_Handoff_Story_Deck.pptx next to the script
```

## The theme

Minimalist and typographic: white ground, one indigo accent, hairline rules, no decoration.
Nothing on a slide is there for looks — every mark is a label, a rule, a number, or a screenshot.

| Role | Hex | Use |
|---|---|---|
| Ink | `14161A` | headlines, the "after" column, card headers |
| Body | `4A4F58` | body copy |
| Muted | `8B9199` | captions, footers, slide index |
| Rule | `E5E7EA` | hairlines, card borders |
| Tint | `F7F8F9` | card fill |
| Accent | `5B52E5` | eyebrows, numerals, the one stat per slide that matters |
| Coral | `C9564A` | aging and regression risk only |
| Dark ground | `121319` | slides 1, 5, 12 |

Indigo and coral are lifted from the dashboard's own UI, so the screenshots sit inside the
palette instead of fighting it.

**Type** — Arial throughout (metric-safe everywhere Office runs), carried by size and weight
contrast rather than font mixing. Courier New appears only on technical metadata: timestamps,
the slide index, card numerals.

**Repeated devices** — a 9pt tracked-out uppercase micro-label above every block; a big numeral
over a small label for every statistic; hairlines where a section changes; a `NN / 12` index
bottom-right. Dark grounds sandwich the argument: open (1), pivot (5), close (12).

**Grid** — 0.75in side margins, 11.833in content width. Eyebrow at y 0.46, title at 0.82,
content from 1.7, footer and index on a shared baseline at 6.83.

## Slide map

| # | Section | Layout |
|---|---|---|
| 1 | Title | dark; masthead over a four-stat row |
| 2 | Overview | two-column thesis, then three step cards current → target |
| 3 | The constraint | 10+ → 2 ratio, two failure blocks, cost band |
| 4 | Why fixes failed | full-width shift-clock exhibit, 12h stat |
| 5 | The reframe | dark; statement slide, two-column contrast |
| 6 | What the shift gets | four numbered questions, dashboard screenshot, ordering rule |
| 7 | Before / after | five-row hairline table |
| 8 | Evidence | 27d 11h stat + risk card, two product screenshots |
| 9 | Autonomy | Slack proof, three zero-stats |
| 10 | Architecture | full-width pipeline exhibit, two notes |
| 11 | Business impact | 2 × 2 value cards |
| 12 | Recommendation | dark; the gap, the ask, what's already controlled |

`assets/` holds the six exhibits (product screenshots and the two diagrams) extracted from the
original deck.
