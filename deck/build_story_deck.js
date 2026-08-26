/**
 * QA Handoff Dashboard — Executive Story Deck
 * Rebuilt on the "Quiet Signal" theme: clean, minimalist, high size-contrast,
 * hairline rules, a lot of white, one indigo accent lifted from the product UI.
 *
 *   node deck/build_story_deck.js [outfile.pptx]
 */

const path = require("path");
const PptxGenJS = require("pptxgenjs");

const OUT = process.argv[2] || path.join(__dirname, "QA_Handoff_Story_Deck.pptx");
const A = (f) => path.join(__dirname, "assets", f);

/* ---------------------------------------------------------------- theme --- */

const C = {
  paper: "FFFFFF",
  ink: "14161A", // headlines
  body: "4A4F58", // body copy
  muted: "8B9199", // captions, slide index
  rule: "E5E7EA", // hairlines
  tint: "F7F8F9", // card fill

  dark: "121319", // dark slide ground
  darkTint: "1D1F28", // dark card fill
  darkRule: "31343F",
  darkBody: "AAAFB9",
  darkMuted: "757B87",

  accent: "5B52E5", // indigo, from the dashboard's ticket-key colour
  accentUp: "9A93F7", // accent for dark grounds
  coral: "C9564A", // aging / risk, from the product's badges
};

const F = { head: "Arial", body: "Arial", mono: "Courier New" };

// 13.333 x 7.5 grid
const M = 0.75; // side margin
const W = 11.833; // content width
const R = M + W; // right edge = 12.583
const FOOT = 6.83; // footer + slide-index baseline

const SLIDES = 12;

/* --------------------------------------------------------------- helpers --- */

const microLabel = (color) => ({
  fontFace: F.head,
  fontSize: 9,
  bold: true,
  charSpacing: 1.7,
  color,
  isTextBox: true,
  margin: 0,
});

/** Section eyebrow, slide title, footer note and slide index. */
function frame(s, { eyebrow, title, titleW = W, note, noteMono = false, n, dark = false }) {
  if (dark) s.background = { color: C.dark };

  if (eyebrow) {
    s.addText(eyebrow.toUpperCase(), {
      x: M,
      y: 0.46,
      w: W,
      h: 0.22,
      ...microLabel(dark ? C.accentUp : C.accent),
      valign: "middle",
    });
  }

  if (title) {
    s.addText(title, {
      x: M,
      y: 0.82,
      w: titleW,
      h: 0.62,
      fontFace: F.head,
      fontSize: 27,
      bold: true,
      charSpacing: -0.3,
      color: dark ? C.paper : C.ink,
      isTextBox: true,
      margin: 0,
      valign: "top",
      lineSpacingMultiple: 1.05,
    });
  }

  if (note) {
    s.addText(note, {
      x: M,
      y: FOOT,
      w: W - 1.1,
      h: 0.3,
      fontFace: noteMono ? F.mono : F.body,
      fontSize: noteMono ? 8.5 : 9.5,
      color: dark ? C.darkMuted : C.muted,
      isTextBox: true,
      margin: 0,
      valign: "middle",
    });
  }

  s.addText(`${String(n).padStart(2, "0")} / ${SLIDES}`, {
    x: R - 1.1,
    y: FOOT,
    w: 1.1,
    h: 0.3,
    fontFace: F.mono,
    fontSize: 8.5,
    color: dark ? C.darkMuted : C.muted,
    align: "right",
    isTextBox: true,
    margin: 0,
    valign: "middle",
  });
}

/** Micro label + body copy stacked in one column. */
function block(s, { x, y, w, label, labelColor, head, headSize = 15, text, textSize = 11.5, dark = false }) {
  let cy = y;
  if (label) {
    s.addText(label.toUpperCase(), {
      x,
      y: cy,
      w,
      h: 0.2,
      ...microLabel(labelColor || (dark ? C.accentUp : C.accent)),
      valign: "middle",
    });
    cy += 0.36;
  }
  if (head) {
    s.addText(head, {
      x,
      y: cy,
      w,
      h: 0.32,
      fontFace: F.head,
      fontSize: headSize,
      bold: true,
      color: dark ? C.paper : C.ink,
      isTextBox: true,
      margin: 0,
      valign: "top",
      lineSpacingMultiple: 1.1,
    });
    cy += headSize > 14 ? 0.42 : 0.36;
  }
  if (text) {
    s.addText(text, {
      x,
      y: cy,
      w,
      h: 1.4,
      fontFace: F.body,
      fontSize: textSize,
      color: dark ? C.darkBody : C.body,
      isTextBox: true,
      margin: 0,
      valign: "top",
      lineSpacingMultiple: 1.3,
    });
  }
}

/** Big numeral over a small label — the deck's one repeated data device. */
function stat(s, { x, y, w, value, valueSize = 26, label, dark = false, color }) {
  s.addText(value, {
    x,
    y,
    w,
    h: valueSize > 32 ? 0.72 : 0.5,
    fontFace: F.head,
    fontSize: valueSize,
    bold: true,
    charSpacing: -0.6,
    color: color || (dark ? C.paper : C.ink),
    isTextBox: true,
    margin: 0,
    valign: "top",
  });
  s.addText(label, {
    x,
    y: y + (valueSize > 32 ? 0.76 : 0.54),
    w,
    h: 0.75,
    fontFace: F.body,
    fontSize: 10,
    color: dark ? C.darkMuted : C.muted,
    isTextBox: true,
    margin: 0,
    valign: "top",
    lineSpacingMultiple: 1.24,
  });
}

function card(s, { x, y, w, h, dark = false }) {
  s.addShape("rect", {
    x,
    y,
    w,
    h,
    fill: { color: dark ? C.darkTint : C.tint },
    line: { color: dark ? C.darkRule : C.rule, width: 0.75 },
  });
}

function hairline(s, { x, y, w, dark = false }) {
  s.addShape("line", { x, y, w, h: 0, line: { color: dark ? C.darkRule : C.rule, width: 0.75 } });
}

/* ------------------------------------------------------------------ deck --- */

const pres = new PptxGenJS();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5
pres.author = "Amanda Chan";
pres.company = "Power Digital Marketing";
pres.title = "The Handoff That Needs No One Awake";

/* --- 01 · title (dark) --------------------------------------------------- */
{
  const s = pres.addSlide();
  frame(s, {
    n: 1,
    dark: true,
    eyebrow: "nova QA Engineering  ·  Case Study",
    note: "Current state, what replaced it, and the one decision that closes the last gap.",
  });

  s.addText("The Handoff That\nNeeds No One Awake", {
    x: M,
    y: 1.42,
    w: 9.2,
    h: 1.95,
    fontFace: F.head,
    fontSize: 43,
    bold: true,
    charSpacing: -0.8,
    color: C.paper,
    isTextBox: true,
    margin: 0,
    valign: "top",
    lineSpacingMultiple: 1.04,
  });

  s.addText("The QA → Production Handoff Dashboard", {
    x: M,
    y: 3.52,
    w: 9.2,
    h: 0.3,
    fontFace: F.body,
    fontSize: 14,
    color: C.darkBody,
    isTextBox: true,
    margin: 0,
  });

  s.addText("AMANDA CHAN   ·   POWER DIGITAL MARKETING", {
    x: M,
    y: 3.92,
    w: 9.2,
    h: 0.26,
    fontFace: F.mono,
    fontSize: 9,
    color: C.darkMuted,
    charSpacing: 0.8,
    isTextBox: true,
    margin: 0,
  });

  hairline(s, { x: M, y: 4.78, w: W, dark: true });

  const col = 2.755;
  const gap = 0.271;
  const stats = [
    ["10+ : 2", "engineers pushing work vs. QA engineers clearing it"],
    ["~1 hr", "of manual triage at every shift start — removed"],
    ["2 × day", "07:00 & 19:00 UTC, zero manual steps"],
    ["60 sec", "to read the whole state of the pipeline"],
  ];
  stats.forEach(([v, l], i) => {
    stat(s, { x: M + i * (col + gap), y: 5.12, w: col, value: v, valueSize: 24, label: l, dark: true });
  });

  s.addNotes(
    "Open in the audience's world, not the tool's. The ratio — 10+ engineers into 2 QA — is the whole 'what is' in one line. Leave the four stat cards unexplained for now; they pay off at the close."
  );
}

/* --- 02 · overview ------------------------------------------------------- */
{
  const s = pres.addSlide();
  frame(s, {
    n: 2,
    eyebrow: "Overview",
    title: "The Thesis and What Is at Stake",
    note: "Each section that follows is one step from current state to target state.",
  });

  block(s, {
    x: M,
    y: 1.85,
    w: 6.5,
    label: "The thesis",
    text:
      "Cross-time-zone handoff was never a communication problem. It is a delivery problem — and once it is treated as one, coordination stops costing anyone a shared working hour.",
    textSize: 15,
  });

  block(s, {
    x: 7.6,
    y: 1.85,
    w: 4.98,
    label: "What is at stake",
    text:
      "Release velocity and regression escapes in every multi-shift team we run. QA is only where it showed first.",
  });

  s.addText("CURRENT STATE", {
    x: M,
    y: 3.72,
    w: 4,
    h: 0.2,
    ...microLabel(C.muted),
  });
  s.addText("TARGET STATE", {
    x: R - 4,
    y: 3.72,
    w: 4,
    h: 0.2,
    ...microLabel(C.muted),
    align: "right",
  });
  hairline(s, { x: M, y: 4.06, w: W });

  const cw = 3.778;
  const steps = [
    ["1", "Constraint", "why earlier fixes failed"],
    ["2", "Change", "what replaced them, with proof"],
    ["3", "Outcome", "impact and the one decision"],
  ];
  steps.forEach(([num, head, sub], i) => {
    const x = M + i * (cw + 0.25);
    card(s, { x, y: 4.32, w: cw, h: 1.62 });
    s.addText(num, {
      x: x + 0.32,
      y: 4.56,
      w: 0.6,
      h: 0.4,
      fontFace: F.head,
      fontSize: 22,
      bold: true,
      color: C.accent,
      isTextBox: true,
      margin: 0,
      valign: "top",
    });
    s.addText(head, {
      x: x + 0.32,
      y: 5.08,
      w: cw - 0.64,
      h: 0.3,
      fontFace: F.head,
      fontSize: 15,
      bold: true,
      color: C.ink,
      isTextBox: true,
      margin: 0,
    });
    s.addText(sub, {
      x: x + 0.32,
      y: 5.42,
      w: cw - 0.64,
      h: 0.4,
      fontFace: F.body,
      fontSize: 10.5,
      color: C.body,
      isTextBox: true,
      margin: 0,
      lineSpacingMultiple: 1.2,
    });
  });

  s.addNotes(
    "The line is the shape of the argument: it moves between current and target state, and each move adds pressure. Say the thesis out loud here and again at the close — one idea, stated as a point of view with the stakes attached."
  );
}

/* --- 03 · the constraint ------------------------------------------------- */
{
  const s = pres.addSlide();
  frame(s, {
    n: 3,
    eyebrow: "The constraint  ·  Current state",
    title: "A Pipeline Fed Faster Than It Can Be Cleared",
    note: "Derived from the case study: ~1 hour of manual triage × 2 shifts × 5 days.",
  });

  s.addText("VOLUME", { x: M, y: 1.85, w: 3, h: 0.2, ...microLabel(C.accent) });

  s.addText("10+", {
    x: M,
    y: 2.16,
    w: 2.1,
    h: 0.78,
    fontFace: F.head,
    fontSize: 44,
    bold: true,
    charSpacing: -1.2,
    color: C.ink,
    isTextBox: true,
    margin: 0,
    valign: "top",
  });
  s.addText("engineers push work into one QA column", {
    x: M,
    y: 2.98,
    w: 2.1,
    h: 0.7,
    fontFace: F.body,
    fontSize: 10,
    color: C.muted,
    isTextBox: true,
    margin: 0,
    valign: "top",
    lineSpacingMultiple: 1.24,
  });

  s.addText("→", {
    x: 2.98,
    y: 2.3,
    w: 0.55,
    h: 0.5,
    fontFace: F.body,
    fontSize: 20,
    color: C.muted,
    align: "center",
    isTextBox: true,
    margin: 0,
  });

  s.addText("2", {
    x: 3.62,
    y: 2.16,
    w: 2.2,
    h: 0.78,
    fontFace: F.head,
    fontSize: 44,
    bold: true,
    charSpacing: -1.2,
    color: C.ink,
    isTextBox: true,
    margin: 0,
    valign: "top",
  });
  s.addText("QA engineers clear it, never at the same time", {
    x: 3.62,
    y: 2.98,
    w: 2.2,
    h: 0.7,
    fontFace: F.body,
    fontSize: 10,
    color: C.muted,
    isTextBox: true,
    margin: 0,
    valign: "top",
    lineSpacingMultiple: 1.24,
  });

  s.addText("Tickets arrive faster than two people can clear them, so In QA floods.", {
    x: M,
    y: 3.88,
    w: 5.1,
    h: 0.6,
    fontFace: F.body,
    fontSize: 11.5,
    color: C.body,
    isTextBox: true,
    margin: 0,
    valign: "top",
    lineSpacingMultiple: 1.3,
  });

  block(s, {
    x: 6.6,
    y: 1.85,
    w: 5.98,
    label: "No context",
    text:
      "Jira says a ticket is In QA. It does not say what changed, what to test, or how long it has waited.",
  });
  hairline(s, { x: 6.6, y: 3.18, w: 5.98 });
  block(s, {
    x: 6.6,
    y: 3.4,
    w: 5.98,
    label: "No memory",
    text:
      "Each shift rebuilt that picture by hand, and it went stale the moment they logged off.",
  });

  card(s, { x: M, y: 4.98, w: W, h: 1.5 });
  s.addText("≈ 10 engineer-hours a week", {
    x: 1.1,
    y: 5.48,
    w: 4.3,
    h: 0.5,
    fontFace: F.head,
    fontSize: 24,
    bold: true,
    charSpacing: -0.6,
    color: C.accent,
    isTextBox: true,
    margin: 0,
    valign: "middle",
  });
  s.addText("spent reconstructing a state that already existed in the system.", {
    x: 5.7,
    y: 5.48,
    w: 6.4,
    h: 0.5,
    fontFace: F.body,
    fontSize: 13,
    color: C.ink,
    isTextBox: true,
    margin: 0,
    valign: "middle",
  });

  s.addNotes(
    "Establish what is, plainly and with no fix in sight. The ratio does the emotional work; the 10 engineer-hours does the analytical work. Resist offering the solution on this slide."
  );
}

/* --- 04 · why earlier fixes failed -------------------------------------- */
{
  const s = pres.addSlide();
  frame(s, {
    n: 4,
    eyebrow: "The constraint  ·  Why earlier fixes failed",
    title: "No Shared Hour Was Ever Available",
    note: "The constraint is structural, not behavioural — which is why every process fix lapsed.",
  });

  s.addImage({ path: A("clock.png"), x: M, y: 1.72, w: W, h: 2.427 });

  s.addText("12 h", {
    x: M,
    y: 4.5,
    w: 3.1,
    h: 0.72,
    fontFace: F.head,
    fontSize: 40,
    bold: true,
    charSpacing: -1,
    color: C.ink,
    isTextBox: true,
    margin: 0,
    valign: "top",
  });
  s.addText(
    "is how long anything one engineer learns at the end of a shift must survive before it reaches the other.",
    {
      x: M,
      y: 5.3,
      w: 3.1,
      h: 1.1,
      fontFace: F.body,
      fontSize: 10.5,
      color: C.body,
      isTextBox: true,
      margin: 0,
      valign: "top",
      lineSpacingMultiple: 1.28,
    }
  );

  block(s, {
    x: 4.6,
    y: 4.5,
    w: 7.98,
    head: "Every proposed fix asked for the same thing.",
    headSize: 17,
    text:
      "A standing sync, a forced overlap, someone's evening. A shared working hour the schedule would not give up — so none of them held.",
    textSize: 12,
  });

  s.addNotes(
    "The point of this slide: the room has to accept that the obvious fixes are already exhausted. Pause after 'none of them held' — this is the moment they should want an answer."
  );
}

/* --- 05 · the reframe (dark) -------------------------------------------- */
{
  const s = pres.addSlide();
  frame(s, { n: 5, dark: true, eyebrow: "Approach  ·  The reframe" });

  s.addText(
    [
      { text: "Stop solving it as a\ncommunication problem.", options: { color: C.darkMuted, breakLine: true } },
      { text: "Solve it as a delivery problem.", options: { color: C.paper } },
    ],
    {
      x: M,
      y: 1.5,
      w: 10.6,
      h: 2.3,
      fontFace: F.head,
      fontSize: 34,
      bold: true,
      charSpacing: -0.7,
      isTextBox: true,
      margin: 0,
      valign: "top",
      lineSpacingMultiple: 1.14,
    }
  );

  s.addText(
    "The two shifts never needed to be awake together. They needed an artifact that is already current the moment each of them logs on.",
    {
      x: M,
      y: 4.02,
      w: 9.6,
      h: 0.7,
      fontFace: F.body,
      fontSize: 14,
      color: C.darkBody,
      isTextBox: true,
      margin: 0,
      valign: "top",
      lineSpacingMultiple: 1.3,
    }
  );

  hairline(s, { x: M, y: 5.0, w: W, dark: true });

  block(s, {
    x: M,
    y: 5.24,
    w: 5.7,
    dark: true,
    label: "Communication fix",
    labelColor: C.darkMuted,
    text: "Asks for a shared hour the schedule will not give up. Lapses within a month.",
  });
  block(s, {
    x: 6.88,
    y: 5.24,
    w: 5.7,
    dark: true,
    label: "Delivery fix",
    labelColor: C.accentUp,
    text: "Asks nothing of anyone. Runs whether or not we remember it exists.",
  });

  s.addNotes(
    "The pivot of the deck: one reframe, in a sentence the room can repeat afterwards. Everything after this slide is consequence, not argument."
  );
}

/* --- 06 · what the shift receives --------------------------------------- */
{
  const s = pres.addSlide();
  frame(s, {
    n: 6,
    eyebrow: "The solution  ·  What the shift receives",
    title: "What the Incoming Shift Now Opens",
    titleW: 7.2,
    note: "One screen at 07:00 — changes, aging watch, module risk, test notes. Every item links back to Jira.",
  });

  s.addImage({ path: A("dashboard.png"), x: 8.15, y: 1.78, w: 4.43, h: 4.21 });

  s.addText("Four questions the shift used to answer by hand — answered on arrival:", {
    x: M,
    y: 1.8,
    w: 7,
    h: 0.24,
    fontFace: F.body,
    fontSize: 11,
    color: C.muted,
    isTextBox: true,
    margin: 0,
  });

  const items = [
    "What moved in the last twelve hours.",
    "Which tickets are stuck, and for how long.",
    "Which tickets share a module and must be regression-tested together.",
    "What each ticket actually requires to test — the developer's Problem / Fix / How to verify, lifted out of the comment thread.",
  ];
  const rowY = [2.24, 2.79, 3.34, 3.89];
  items.forEach((t, i) => {
    s.addText(String(i + 1), {
      x: M,
      y: rowY[i],
      w: 0.34,
      h: 0.28,
      fontFace: F.head,
      fontSize: 13,
      bold: true,
      color: C.accent,
      isTextBox: true,
      margin: 0,
      valign: "top",
    });
    s.addText(t, {
      x: M + 0.42,
      y: rowY[i],
      w: 6.25,
      h: i === 3 ? 0.7 : 0.45,
      fontFace: F.body,
      fontSize: 11.5,
      color: C.ink,
      isTextBox: true,
      margin: 0,
      valign: "top",
      lineSpacingMultiple: 1.26,
    });
  });

  card(s, { x: M, y: 4.94, w: 7, h: 1.32 });
  s.addText("ORDERING IS A DESIGN DECISION", {
    x: 1.05,
    y: 5.16,
    w: 6.4,
    h: 0.2,
    ...microLabel(C.accent),
  });
  s.addText(
    "Tickets rank by time in QA, because a ticket sitting on Staging accumulates merge-conflict risk the longer it sits. Triaging by age is how builds get finished instead of reworked.",
    {
      x: 1.05,
      y: 5.46,
      w: 6.4,
      h: 0.85,
      fontFace: F.body,
      fontSize: 10.5,
      color: C.body,
      isTextBox: true,
      margin: 0,
      valign: "top",
      lineSpacingMultiple: 1.26,
    }
  );

  s.addNotes(
    "The first look at the target state. Show the artifact, then go straight to the ordering rule — a CTO reads ranking logic as risk management, not UI."
  );
}

/* --- 07 · before and after ---------------------------------------------- */
{
  const s = pres.addSlide();
  frame(s, {
    n: 7,
    eyebrow: "Before and after  ·  Five gaps closed",
    title: "Before and After, Gap by Gap",
    note: "Each gap above cost the team a full shift cycle. One artifact closes all five.",
  });

  const LX = M,
    LW = 5.7,
    RX = 6.98,
    RW = 5.6;

  s.addText("BEFORE", { x: LX, y: 1.72, w: LW, h: 0.2, ...microLabel(C.muted) });
  s.addText("AFTER", { x: RX, y: 1.72, w: RW, h: 0.2, ...microLabel(C.accent) });

  const rows = [
    [
      "A write-up sits six comments deep (NOVA-1747).",
      "It arrives on the ticket. Testing starts in minutes, not after a triage pass.",
    ],
    [
      "An end-of-day question waits a full lap. NOVA-1710 cycled In QA ↔ Back to Development for days — mostly clock, not effort.",
      "Open questions lead the handoff and get answered on the next shift instead of the next loop.",
    ],
    [
      "Nothing tracked time in QA. One ticket held ~10 days on a request for testing details — a two-minute answer.",
      "The aging watch names the oldest tickets every 12 hours and flags them at two and three days.",
    ],
    [
      "One shift ships a module while the other still holds related tickets. Nobody sees the overlap; regressions ship.",
      "Shared-module tickets are flagged when they span stages. That flag is the regression test plan.",
    ],
    [
      "The report existed only if someone awake ran it.",
      "It posts at 07:00 and 19:00 UTC whether anyone is awake or not.",
    ],
  ];

  const top = 2.06;
  const rh = 0.9;
  rows.forEach(([before, after], i) => {
    const y = top + i * rh;
    hairline(s, { x: M, y, w: W });
    s.addText(before, {
      x: LX,
      y: y + 0.16,
      w: LW,
      h: rh - 0.24,
      fontFace: F.body,
      fontSize: 10,
      color: C.body,
      isTextBox: true,
      margin: 0,
      valign: "top",
      lineSpacingMultiple: 1.24,
    });
    s.addText("→", {
      x: 6.42,
      y: y + 0.16,
      w: 0.4,
      h: 0.3,
      fontFace: F.body,
      fontSize: 12,
      color: C.accent,
      align: "center",
      isTextBox: true,
      margin: 0,
    });
    s.addText(after, {
      x: RX,
      y: y + 0.16,
      w: RW,
      h: rh - 0.24,
      fontFace: F.body,
      fontSize: 10,
      color: C.ink,
      isTextBox: true,
      margin: 0,
      valign: "top",
      lineSpacingMultiple: 1.24,
    });
  });
  hairline(s, { x: M, y: top + rows.length * rh, w: W });

  s.addNotes(
    "Contrast is the mechanism. Read each pair as a beat — what is, then what could be — and do not linger. The five passes are the engine of the middle act."
  );
}

/* --- 08 · evidence ------------------------------------------------------ */
{
  const s = pres.addSlide();
  frame(s, {
    n: 8,
    eyebrow: "Evidence  ·  Release risk made visible",
    title: "Stalls and Regression Risk, Named Every Twelve Hours",
    note:
      "For a VP of Product: the tickets most likely to slip a release surface themselves before anyone goes looking for them.",
  });

  const IX = 6.68,
    IW = 5.9;
  s.addImage({ path: A("aging-watch.png"), x: IX, y: 1.72, w: IW, h: 2.905 });
  s.addImage({ path: A("module-risk.png"), x: IX, y: 4.82, w: IW, h: 1.764 });

  s.addText("27d 11h", {
    x: M,
    y: 1.9,
    w: 5.4,
    h: 0.72,
    fontFace: F.head,
    fontSize: 40,
    bold: true,
    charSpacing: -1,
    color: C.coral,
    isTextBox: true,
    margin: 0,
    valign: "top",
  });
  s.addText("oldest ticket in QA — surfaced without anyone asking", {
    x: M,
    y: 2.7,
    w: 5,
    h: 0.5,
    fontFace: F.body,
    fontSize: 11.5,
    color: C.body,
    isTextBox: true,
    margin: 0,
    valign: "top",
    lineSpacingMultiple: 1.28,
  });

  card(s, { x: M, y: 3.52, w: 5.4, h: 1.92 });
  s.addText("HIGH RISK MODULE", { x: 1.05, y: 3.76, w: 4.8, h: 0.2, ...microLabel(C.coral) });
  s.addText("Intelligence · Creative Reports", {
    x: 1.05,
    y: 4.06,
    w: 4.8,
    h: 0.3,
    fontFace: F.head,
    fontSize: 15,
    bold: true,
    color: C.ink,
    isTextBox: true,
    margin: 0,
  });
  s.addText(
    "4 in QA · 1 Ready · 2 in Prod, at the same time. One module carrying tickets across three stages is where a regression escapes.",
    {
      x: 1.05,
      y: 4.45,
      w: 4.8,
      h: 0.9,
      fontFace: F.body,
      fontSize: 10.5,
      color: C.body,
      isTextBox: true,
      margin: 0,
      valign: "top",
      lineSpacingMultiple: 1.26,
    }
  );

  s.addNotes(
    "Analytical proof, placed immediately after the emotional turn. Both exhibits are unedited product screenshots — for a technical audience the artifact is the argument."
  );
}

/* --- 09 · autonomy ------------------------------------------------------ */
{
  const s = pres.addSlide();
  frame(s, {
    n: 9,
    eyebrow: "Autonomous delivery  ·  Proof in production",
    title: "Neither of These Was Sent by a Person",
    titleW: 7,
    note: "#qa-daily-reports — 25 Aug 16:11 UTC and 26 Aug 01:10 UTC, unattended.",
    noteMono: true,
  });

  s.addImage({ path: A("slack-handoffs.png"), x: 7.28, y: 1.76, w: 5.3, h: 4.261 });

  s.addText(
    "Two consecutive handoffs in #qa-daily-reports, twelve hours apart. No one triggered either one, and no machine involved was awake.",
    {
      x: M,
      y: 1.82,
      w: 6.2,
      h: 1.1,
      fontFace: F.body,
      fontSize: 14,
      color: C.ink,
      isTextBox: true,
      margin: 0,
      valign: "top",
      lineSpacingMultiple: 1.3,
    }
  );

  hairline(s, { x: M, y: 3.2, w: 6.2 });

  block(s, {
    x: M,
    y: 3.42,
    w: 6.2,
    label: "Why autonomy is the load-bearing part",
    text:
      "Autonomy is what makes the other four gains count. A lens that works only sometimes is a lens the shift stops opening.",
  });

  const cw = 1.93;
  [
    ["0", "manual steps per cycle"],
    ["0", "machines awake"],
    ["2", "posts a day"],
  ].forEach(([v, l], i) => {
    stat(s, { x: M + i * (cw + 0.2), y: 5.06, w: cw, value: v, valueSize: 30, label: l, color: C.accent });
  });

  s.addNotes(
    "This is the one image the room repeats afterwards. Say the line — 'no one triggered either one, and no machine involved was awake' — then stop talking for a beat and let it land."
  );
}

/* --- 10 · architecture -------------------------------------------------- */
{
  const s = pres.addSlide();
  frame(s, {
    n: 10,
    eyebrow: "Architecture  ·  Four parts, zero manual steps",
    title: "The Part That Generalizes",
    note: "Any recurring cross-shift task can become an unattended service.",
  });

  s.addImage({ path: A("architecture.png"), x: M, y: 1.68, w: W, h: 3.15 });

  hairline(s, { x: M, y: 5.08, w: W });

  block(s, {
    x: M,
    y: 5.3,
    w: 5.79,
    label: "The three reusable pieces",
    text:
      "A versioned generator, a scheduled cloud routine, and standing connections to the systems of record. Nothing here is QA-specific.",
    textSize: 11,
  });
  block(s, {
    x: 6.79,
    y: 5.3,
    w: 5.79,
    label: "The report cannot show the wrong ticket",
    text:
      "Jira's API occasionally returns a mismatched issue, so the generator cross-checks every ticket key and re-fetches on mismatch.",
    textSize: 11,
  });

  s.addNotes(
    "For the CTO this is the slide that matters: the architecture is boring on purpose and reusable by design. Keep it to 60 seconds — the pattern, not the plumbing."
  );
}

/* --- 11 · business impact ----------------------------------------------- */
{
  const s = pres.addSlide();
  frame(s, {
    n: 11,
    eyebrow: "Business impact",
    title: "What This Buys Product and Engineering",
    note: "The value accrues to the teams reading the handoff, not to the tool that writes it.",
  });

  const cards = [
    [
      "The same 60-second read",
      "What is moving down the pipeline, what has been sitting long enough to warrant attention, and where a module carries regression risk across stages. No status meeting required.",
    ],
    [
      "Status-chasing becomes a link",
      "Long-standing tickets surface themselves instead of waiting to be asked about, and the tickets most likely to slip a release are flagged before anyone looks.",
    ],
    [
      "Ramp without adding a meeting",
      "As QA grows, the same view is where a new member picks up work and sees what happened while they were away.",
    ],
    [
      "The pattern, not the tool",
      "A multi-shift organisation lives or stalls on the quality of its async handoffs. This is the template for the rest of them.",
    ],
  ];

  const cw = 5.79,
    ch = 2.25;
  cards.forEach(([head, text], i) => {
    const x = M + (i % 2) * (cw + 0.25);
    const y = 1.78 + Math.floor(i / 2) * (ch + 0.25);
    card(s, { x, y, w: cw, h: ch });
    s.addText(String(i + 1).padStart(2, "0"), {
      x: x + 0.35,
      y: y + 0.28,
      w: 1,
      h: 0.22,
      fontFace: F.mono,
      fontSize: 9.5,
      bold: true,
      charSpacing: 1,
      color: C.accent,
      isTextBox: true,
      margin: 0,
    });
    s.addText(head, {
      x: x + 0.35,
      y: y + 0.62,
      w: cw - 0.7,
      h: 0.32,
      fontFace: F.head,
      fontSize: 16,
      bold: true,
      color: C.ink,
      isTextBox: true,
      margin: 0,
    });
    s.addText(text, {
      x: x + 0.35,
      y: y + 1.04,
      w: cw - 0.7,
      h: 1.0,
      fontFace: F.body,
      fontSize: 11,
      color: C.body,
      isTextBox: true,
      margin: 0,
      valign: "top",
      lineSpacingMultiple: 1.3,
    });
  });

  s.addNotes(
    "Describe the end state in their terms — their release risk, their ramp time, their meetings — never the builder's. Hand the win to the room."
  );
}

/* --- 12 · recommendation (dark) ----------------------------------------- */
{
  const s = pres.addSlide();
  frame(s, {
    n: 12,
    dark: true,
    eyebrow: "Recommendation  ·  The one open dependency",
    title: "One Decision Closes the Last Gap",
    note: "AMANDA CHAN  ·  POWER DIGITAL MARKETING  ·  2026",
    noteMono: true,
  });

  block(s, {
    x: M,
    y: 1.78,
    w: 7.1,
    dark: true,
    label: "The gap",
    text:
      "The generator runs from a personal GitHub repository — not SOC 2 compliant. The interim mitigation is to omit all PII, and it holds — but it costs the one field the handoff most needs: which developer owns a stall. The incoming shift still returns to the board for it, which is the exact lookup this exists to remove.",
    textSize: 11.5,
  });

  s.addShape("rect", {
    x: M,
    y: 3.72,
    w: 7.1,
    h: 1.42,
    fill: { color: "1E1B44" },
    line: { color: "342E6B", width: 0.75 },
  });
  s.addText("THE ASK", { x: 1.05, y: 3.96, w: 6.5, h: 0.2, ...microLabel(C.accentUp) });
  s.addText(
    "Land the GitHub Enterprise migration (owned by Anton). Attribution goes back in and the last manual lookup disappears.",
    {
      x: 1.05,
      y: 4.28,
      w: 6.5,
      h: 0.7,
      fontFace: F.body,
      fontSize: 12.5,
      color: C.paper,
      isTextBox: true,
      margin: 0,
      valign: "top",
      lineSpacingMultiple: 1.28,
    }
  );

  s.addText("ALREADY CONTROLLED", { x: 8.4, y: 1.78, w: 4.18, h: 0.2, ...microLabel(C.darkMuted) });
  const controlled = [
    ["Data integrity", "every ticket key cross-checked, re-fetched on mismatch"],
    ["Connection drift", "standing Jira and Slack auth — administrative, owned with IT"],
    ["Scope creep", "changes-first by design; a 60-second read gets opened"],
    ["Ownership", "start-of-shift ownership convention ships with the rollout"],
  ];
  controlled.forEach(([label, text], i) => {
    const y = 2.18 + i * 0.76;
    s.addText(
      [
        { text: label, options: { bold: true, color: C.paper } },
        { text: " — " + text, options: { color: C.darkBody } },
      ],
      {
        x: 8.4,
        y,
        w: 4.18,
        h: 0.66,
        fontFace: F.body,
        fontSize: 10,
        isTextBox: true,
        margin: 0,
        valign: "top",
        lineSpacingMultiple: 1.26,
      }
    );
    if (i < controlled.length - 1) hairline(s, { x: 8.4, y: y + 0.64, w: 4.18, dark: true });
  });

  hairline(s, { x: M, y: 5.62, w: W, dark: true });
  s.addText("Handoff stopped being a communication problem the moment it became a delivery one.", {
    x: M,
    y: 5.88,
    w: W,
    h: 0.5,
    fontFace: F.head,
    fontSize: 17,
    bold: true,
    charSpacing: -0.3,
    color: C.paper,
    isTextBox: true,
    margin: 0,
    valign: "middle",
  });

  s.addNotes(
    "End on one action, stated as a decision someone in this room can actually make. Repeat the thesis as the last sentence, then stop — no summary slide after this one."
  );
}

pres.writeFile({ fileName: OUT }).then(() => console.log("wrote " + OUT));
