---
name: design
description: One stop for every design-flavored task — brand identity & voice, design tokens & systems, UI/UX intelligence (50+ styles, 161 palettes, 57 font pairings, 99 UX guidelines), micro-interaction polish (animation framework, perf rules), shadcn/Tailwind code patterns, logo generation (55 styles, Gemini AI), corporate identity programs (50 deliverables, CIP mockups), HTML presentations (Chart.js), banner design (22 styles, social/ads/web/print), icon design (15 styles, SVG, Gemini), social media photos (HTML→screenshot), and font catalogs. Use whenever the user wants to design, generate, or polish anything visual or brand-related — logos, banners, social images, icons, brand voice, design tokens, design system, color palettes, font choices, presentations, slides, UI intelligence, UX guidelines, animation decisions, polish details, shadcn components, Tailwind patterns, dark/light/gray theming, or wants to "design", "make", "create", or "generate" any visual or brand asset. Triggers on /design, /brand, /design-system, /ui-styling, /banner-design, /slides, /ui-ux-pro-max, /emil-design-eng, and on phrases like "design a logo", "create a brand identity", "make a banner for X", "generate a social post", "build a pitch deck", "design icons", "set up design tokens", "what palette should I use", "what font pairs with X", "polish this UI", "should this animate", "what easing should I use", "make this feel premium", "shadcn component for X", "tailwind pattern for Y". Platforms: Facebook, Twitter/X, LinkedIn, YouTube, Instagram, Pinterest, TikTok, Threads, Google Ads, print. Stacks: React, Next.js, Vue, Svelte, SwiftUI, React Native, Flutter, Tailwind, shadcn/ui, HTML/CSS.
argument-hint: "[domain] [args]"
---

# design

The unified design skill. Every domain — brand voice, design tokens, UI intelligence, polish, code patterns, logos, CIPs, slides, banners, icons, social photos — lives here. SKILL.md is a thin router; depth lives in `references/` and `scripts/`.

## Domain map

| Domain | When | Where |
|---|---|---|
| **brand** | Brand voice, identity, messaging, asset management | `references/brand/` |
| **system** | Design tokens (primitive→semantic→component), CSS vars, spacing/typography, component specs | `references/system/` |
| **intelligence** | UI/UX choices: styles, palettes, font pairings, product-type patterns, UX guidelines, chart types | `references/intelligence.md` |
| **polish** | Animation framework, micro-interactions, easing, perf rules, Emil-style craft | `references/polish.md` |
| **code** | shadcn/ui + Radix patterns, Tailwind, accessibility, dark mode, canvas + fonts | `references/code/` |
| **logo** | Logo design — 55 styles, 30 palettes, 25 industries, Gemini AI generation | `references/logo-*.md`, `scripts/logo/` |
| **cip** | Corporate Identity Program — 50 deliverables, HTML mockups | `references/cip-*.md`, `scripts/cip/` |
| **banner** | Banners — social, ads, web hero, print. 22 styles, all platform sizes | `references/banner-sizes-and-styles.md` |
| **slides** | HTML presentations with Chart.js — layouts, copy formulas, strategies | `references/slides-*.md` |
| **icon** | SVG icons — 15 styles, Gemini 3.1 Pro generation | `references/icon-design.md`, `scripts/icon/` |
| **social-photos** | Multi-platform social images — HTML/CSS → screenshot | `references/social-photos-design.md` |

Pick the domain that matches the task. Many tasks span multiple domains — read the relevant references together.

## Five principles across all domains

1. **Read the existing project first.** Brand voice, design tokens, theme files, sibling components. Never ship a generic template that ignores what's already there.
2. **Three themes always.** Dark, light, AND gray. Every color, border, shadow, surface must read correctly in all three. Semantic tokens — never hardcode colors that break in one theme.
3. **Behavior preservation when redesigning existing code.** Only presentation changes. Routes, handlers, contracts, side effects stay identical.
4. **Every SVG is transparent behind its drawing.** No full-canvas rect, no `background` on the root element. A ground belongs to whatever renders the file, as a class, so one drawing reads on a dark band, a light card, and a page that changes theme under it. `~/.intelligence/tools/svg-guard.py fix <path>` strips one; a `Write`/`Edit` hook and a `git commit` hook refuse a new one; gates PLT-05 and AST-17 hold it.
5. **Draw only what can come out right.** Forty or more drawn elements, most of them rectangles and straight segments, is a scene rather than a mark, and it does not end up looking like the thing it depicts however long it is adjusted. Reach for a photograph, a real exported asset, or a mark simple enough to be right — a silhouette, a wordmark, a single shape. Gate PLT-07 measures it, and the same hook refuses a new one.

---

## Brand

Brand voice, visual identity, messaging frameworks, asset management, brand consistency.

Read in order:
- `references/brand/_overview.md` — workflow and decision tree
- The remaining `references/brand/*.md` files for specific deliverables

Scripts: `scripts/brand/`. Templates: `templates/brand/`.

Activate for: branded content, tone of voice, marketing assets, brand compliance, style guides.

---

## System (design tokens)

Three-layer tokens (primitive → semantic → component), CSS variables, spacing/typography scales, component specifications.

Read in order:
- `references/system/_overview.md` — token architecture
- The remaining `references/system/*.md` files for component specs and per-token-type guidance

Scripts: `scripts/system/`. Templates: `templates/system/`. Data: `data/system/`.

Activate for: design tokens, semantic color systems, spacing/type scales, component spec authoring.

---

## Intelligence (UI/UX choices)

Macro design decisions — style language, palette, fonts, product-type patterns, chart types.

Read: `references/intelligence.md` (full library — 50+ styles, 161 palettes, 57 font pairings, 161 product types, 99 UX guidelines, 25 chart types across 10 stacks).

Consult when starting a redesign or new UI and needing direction decisions. Pair with **polish** for micro details.

---

## Polish (micro-interactions)

Polish philosophy, animation decisions, micro-interactions, perf rules.

Read: `references/polish.md`.

Key reference points (always check the file for the full framework):
- **Animation decision tree** — should it animate at all? frequency × purpose
- **Easing curves** — strong custom cubic-beziers; never `ease-in` on UI
- **Durations** — cap UI motion at 300ms; element→duration table
- **Polish checklist** — `transition: all` → fix; `scale(0)` entry → fix; missing `:active` → fix
- **Perf rules** — only animate `transform`+`opacity`; full transform strings under Framer Motion load
- **Scroll-driven animation** — scroll-as-playhead (scrub) vs scroll-triggered (reveal); house rule of ≥1 driven section per page; `useScroll`/`useTransform`/`useSpring`, hardware-accelerated full-transform strings, reduced-motion collapse

Always consult alongside `intelligence` on visual work — direction sets where the eye goes; polish makes it feel premium.

---

## Code

shadcn/ui (Radix UI + Tailwind), Tailwind CSS utility-first, canvas-based visuals, accessibility-first patterns.

Read in order:
- `references/code/_overview.md` — workflow and routing
- The remaining `references/code/*.md` files for component patterns (dialogs, forms, tables, dropdowns, dark mode, theming)

**Always, on any form:** kill the browser autofill yellow/blue background. Autofillable inputs (email, password, name, etc.) get a hardcoded pale-yellow (Chromium) or blue (Firefox) bg via `:-webkit-autofill` that ignores your theme and looks broken on dark/gray surfaces. Audit every form for it and repaint it to the field's real surface token. Fix in `references/code/shadcn-components.md` → "ALWAYS kill the browser autofill yellow/blue background".

Scripts: `scripts/code/`. Font assets: `canvas-fonts/`.

Activate for: building UIs, implementing design systems, responsive layouts, accessible components, theme customization, dark mode, visual designs/posters, consistent styling patterns.

---

## Logo

55+ styles, 30 color palettes, 25 industry guides. Gemini Nano Banana models.

### Generate a design brief

```bash
python3 ~/.intelligence/skills/design/scripts/logo/search.py "tech startup modern" --design-brief -p "BrandName"
```

### Search styles / colors / industries

```bash
python3 ~/.intelligence/skills/design/scripts/logo/search.py "minimalist clean" --domain style
python3 ~/.intelligence/skills/design/scripts/logo/search.py "tech professional" --domain color
python3 ~/.intelligence/skills/design/scripts/logo/search.py "healthcare medical" --domain industry
```

### Generate with AI

Generate against white, deliver with alpha. White gives the model a clean field to draw a
mark on; a white box behind the mark on every surface that is not white is a broken
deliverable. `scripts/logo/transparent.py` floods the background in from the border, so
white inside the mark — a counter, a knockout, a highlight — survives. Generation runs it
automatically; run it by hand on anything that arrived another way.

```bash
python3 ~/.intelligence/skills/design/scripts/logo/generate.py --brand "TechFlow" --style minimalist --industry tech
python3 ~/.intelligence/skills/design/scripts/logo/generate.py --prompt "coffee shop vintage badge" --style vintage
```

**IMPORTANT:** When scripts fail, fix them directly.

After generation, ask the user about HTML preview via `AskUserQuestion`. If yes, build a gallery using `intelligence` + `polish`.

Deeper: `references/logo-design.md`, `references/logo-style-guide.md`, `references/logo-color-psychology.md`, `references/logo-prompt-engineering.md`.

---

## CIP (Corporate Identity Program)

50 deliverables (business cards, letterheads, signage, vehicle wraps, uniforms, swag) across industries and styles, with HTML mockup output.

### Generate a CIP brief

```bash
python3 ~/.intelligence/skills/design/scripts/cip/search.py "tech startup" --cip-brief -b "BrandName"
```

### Search domains

```bash
python3 ~/.intelligence/skills/design/scripts/cip/search.py "business card letterhead" --domain deliverable
python3 ~/.intelligence/skills/design/scripts/cip/search.py "luxury premium elegant" --domain style
python3 ~/.intelligence/skills/design/scripts/cip/search.py "hospitality hotel" --domain industry
python3 ~/.intelligence/skills/design/scripts/cip/search.py "office reception" --domain mockup
```

### Generate

```bash
# Single deliverable
python3 ~/.intelligence/skills/design/scripts/cip/generate.py --brand "TopGroup" --logo /path/to/logo.png --deliverable "business card" --industry "consulting"

# Full set
python3 ~/.intelligence/skills/design/scripts/cip/generate.py --brand "TopGroup" --logo /path/to/logo.png --industry "consulting" --set

# Higher-quality model
python3 ~/.intelligence/skills/design/scripts/cip/generate.py --brand "TopGroup" --logo logo.png --deliverable "business card" --model pro

# Without a brand logo asset
python3 ~/.intelligence/skills/design/scripts/cip/generate.py --brand "TechFlow" --deliverable "business card" --no-logo-prompt
```

Models: `flash` (default, `gemini-2.5-flash-image`), `pro` (`gemini-3-pro-image-preview`).

### Render HTML preview

```bash
python3 ~/.intelligence/skills/design/scripts/cip/render-html.py --brand "TopGroup" --industry "consulting" --images /path/to/cip-output
```

Deeper: `references/cip-design.md`, `references/cip-style-guide.md`, `references/cip-deliverable-guide.md`, `references/cip-prompt-engineering.md`.

---

## Slides (HTML presentations)

Strategic HTML presentations with Chart.js, design tokens, responsive layouts, copywriting formulas.

Load `references/slides-create.md` for the creation workflow.

| Topic | File |
|---|---|
| Creation guide | `references/slides-create.md` |
| Layout patterns | `references/slides-layout-patterns.md` |
| HTML template | `references/slides-html-template.md` |
| Copywriting | `references/slides-copywriting-formulas.md` |
| Strategies | `references/slides-strategies.md` |
| Slide types index | `references/slides.md` |

---

## Banner (social, ads, web hero, print)

22 art-direction styles across social, ads, web, print.

Load `references/banner-sizes-and-styles.md` for complete sizes and styles reference.

### Workflow

1. **Gather requirements** via `AskUserQuestion` — purpose, platform, content, brand, style, quantity
2. **Direction** — pull from `intelligence` (palettes/typography) + `brand`
3. **Design** — HTML/CSS banner; generate visuals with `ai-artist`/`ai-multimodal` if available
4. **Export** — screenshot to PNG at exact dimensions
5. **Present** — show all options side-by-side, iterate on feedback

### Quick size reference

| Platform | Type | Size (px) |
|---|---|---|
| Facebook | Cover | 820 × 312 |
| Twitter/X | Header | 1500 × 500 |
| LinkedIn | Personal | 1584 × 396 |
| YouTube | Channel art | 2560 × 1440 |
| Instagram | Story | 1080 × 1920 |
| Instagram | Post | 1080 × 1080 |
| Google Ads | Med Rectangle | 300 × 250 |
| Website | Hero | 1920 × 600–1080 |

### Top styles

| Style | Best for |
|---|---|
| Minimalist | SaaS, tech |
| Bold typography | Announcements |
| Gradient | Modern brands |
| Photo-based | Lifestyle, e-com |
| Geometric | Tech, fintech |
| Glassmorphism | SaaS, apps |
| Neon/Cyberpunk | Gaming, events |

### Design rules

- Safe zones: critical content in central 70–80%
- One CTA per banner, bottom-right, min 44px height
- Max 2 fonts, min 16px body, ≥32px headline
- Text under 20% for ads (Meta penalizes)
- Print: 300 DPI, CMYK, 3–5mm bleed

---

## Icon (SVG, Gemini 3.1 Pro)

15 styles, 12 categories. Gemini 3.1 Pro Preview generates SVG text output.

### Single icon

```bash
python3 ~/.intelligence/skills/design/scripts/icon/generate.py --prompt "settings gear" --style outlined
python3 ~/.intelligence/skills/design/scripts/icon/generate.py --prompt "shopping cart" --style filled --color "#6366F1"
python3 ~/.intelligence/skills/design/scripts/icon/generate.py --name "dashboard" --category navigation --style duotone
```

### Batch variations

```bash
python3 ~/.intelligence/skills/design/scripts/icon/generate.py --prompt "cloud upload" --batch 4 --output-dir ./icons
```

### Multi-size export

```bash
python3 ~/.intelligence/skills/design/scripts/icon/generate.py --prompt "user profile" --sizes "16,24,32,48" --output-dir ./icons
```

Deeper: `references/icon-design.md`.

---

## Social photos (multi-platform HTML→screenshot)

Multi-platform social images: HTML/CSS → screenshot export. Uses **brand**, **system**, **intelligence**.

Read: `references/social-photos-design.md`.

Workflow:
1. **Brand inputs** — pull from `references/brand/`
2. **Token inputs** — pull from `references/system/`
3. **Direction** — pick style/palette/typography from `references/intelligence.md`
4. **Design** — build HTML per idea × platform size
5. **Polish** — apply `references/polish.md` checklist
6. **Export** — render to images via headless browser

---

## Cross-domain workflows

Common bundles:

- **Brand launch** — brand → logo → cip → system (digital tokens) → social-photos (launch images)
- **Product UI** — intelligence (direction) → polish (micro) → code (implementation) → system (tokens)
- **Pitch deck** — brand (voice) → intelligence (palette/fonts/chart types) → slides (creation)
- **Campaign** — brand → intelligence → banner (multi-platform) → social-photos (companion images)

---

## Coordination with other skills

- **`revamp`** — when *redesigning existing UI*. Revamp orchestrates `intelligence` + `polish` + `code` from here.
- **`input-styling`** — for input controls (dropdowns, selects, search, date/time pickers, autocomplete, tooltips, hovers, calendars). Surface-aware three-theme styling already worked out. Don't hand-style inputs from this skill.
- **`organize`** — for refactoring code structure (not styling). Pair when a redesign also needs file moves/splits.
- **`/release`** — never run git directly. Invoke only when the user explicitly asks to commit/push/ship.

## Reference index

| Path | Content |
|---|---|
| `references/brand/` | Brand voice, identity, messaging (from former `brand` skill) |
| `references/system/` | Design tokens, specs (from former `design-system` skill) |
| `references/code/` | shadcn/Tailwind/Radix patterns, accessibility, theming (from former `ui-styling` skill) |
| `references/intelligence.md` | UI/UX intelligence library (from former `ui-ux-pro-max` skill) |
| `references/polish.md` | Polish philosophy & animation framework (from former `emil-design-eng` skill) |
| `references/logo-*.md` | Logo design, style guide, color psychology, prompt engineering |
| `references/cip-*.md` | CIP design, style guide, deliverable guide, prompt engineering |
| `references/slides-*.md` + `references/slides.md` | Slides creation, layouts, template, copy, strategies |
| `references/banner-sizes-and-styles.md` | Banner platform sizes + style catalog |
| `references/icon-design.md` | Icon style catalog + generation guidance |
| `references/social-photos-design.md` | Multi-platform social image workflow |
| `references/design-routing.md` | Internal routing reference |
| `scripts/{logo,cip,icon,brand,system,code}/` | Generation/automation scripts per domain |
| `templates/{brand,system}/` | Reusable templates |
| `data/{logo,cip,icon,system}/` | Domain data (style lists, palettes, presets) |
| `canvas-fonts/` | Font assets for canvas/poster generation |
