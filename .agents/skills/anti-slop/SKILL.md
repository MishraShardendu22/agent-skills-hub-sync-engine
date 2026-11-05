---
name: anti-slop
description: "Comprehensive multi-domain anti-slop rulebook (miqdadbadjuber/anti-slop): stops AI coding agents shipping generic UI, filler copy, AI comment slop, unresponsive mobile layouts, and inaccessible color contrast. Enforces R-01 to R-38, Craftsmanship Standards (C-1 to C-5), and 4-Block Delivery Gate across UI, Copywriting, Human Usability, Mobile Layout, and Code Comments."
scope: generic
---

# Anti Slop: Multi-Domain Rules for AI Coding Agents

> Source: `miqdadbadjuber/anti-slop` (https://github.com/miqdadbadjuber/anti-slop)
> A comprehensive architectural filter that stops AI coding agents from producing generic UI, filler copy, narrative comment noise, broken mobile layouts, and inaccessible color contrast.
> **A filter, not a style guide**: no prescribed colors, fonts, or layouts—aesthetic and technical direction stays yours.

---

## 1. Operating Principles & Usage Modes

### Two Usage Modes
Before starting work, resolve the operating mode following this precedence:
1. **Explicit Session Instruction**: (e.g. "run antislop in mode 1", "audit this with antislop").
2. **Global Preference**: Saved project preference.
3. **Ask the User**: If mode is unresolved, ask during/after.

For a resolved mode, announce once:
`antislop active: <mode> (<source>).`
(e.g., `antislop active: during (session override).` or `antislop active: after (global preference).`).

- **Mode 1 (During)**: Active guidance while writing code, copy, or markup. Every decision is filtered in real time before files are written.
- **Mode 2 (After)**: Post-hoc audit and surgical refactoring. Review existing work against the 4-Block Delivery Gate and report or fix discrepancies without rewriting functional code.

### The Craftsmanship Standard (C-1 to C-5)
- **C-1 (Intentionality)**: Every visual element, color, and comment must serve an identifiable operational or domain purpose. If you cannot articulate why an element exists, delete it.
- **C-2 (Functional Completeness)**: Shipped components must be complete and interactive. Never deliver mock buttons that do nothing, empty modals, dead links, or truncated logic disguised as finished.
- **C-3 (Content-Driven Composition)**: Layouts must flow from real domain data, not generic marketing grids or fixed card templates.
- **C-4 (Resilience)**: Interfaces must handle variable text lengths, dynamic viewports (375px to 1440px+), and human diversity (keyboard access, high contrast, on-screen keyboards).
- **C-5 (Evidence Over Claims)**: Write only verifiable facts. Never synthesize fake testimonials, synthetic metrics, or placeholder praise.

---

## 2. The 38 Mandatory Rules (R-01 to R-38)

### Group 1: Hard Gate (Absolute — Zero Exceptions)
- **R-02 (Copywriting)**: No em dashes (`—`), no AI hype buzzwords, no assistant conversational chatter, no fabricated testimonials.
- **R-03 (Mobile Responsiveness)**: Mobile is an intentional reflow, not shrunk desktop. Full support down to 320px without horizontal overflow.
- **R-17 (Data & Numbers)**: Never invent performance metrics, uptime figures, or customer statistics.
- **R-18 (Testimonials)**: Never generate fake quotes, avatars, or company endorsements.
- **R-23 (Clarification & Assets)**: Never generate stock illustrations or AI art without explicit direction.
- **R-24 (Navigation)**: Nav items must link to real, existing routes or anchors.
- **R-25 (Color Contrast)**: Text must satisfy WCAG 2.x AA: 4.5:1 normal text, 3.0:1 large text (18px+ or 14px bold) and graphical controls.
- **R-26 (Interactive Elements)**: Controls that look clickable must have working event handlers, focus states, and visible states.
- **R-27 (UI States)**: All interactive views must handle loading, empty, active, and error states gracefully.
- **R-28 (FAQ & Accordions)**: Answer real domain questions; never fill space with generic placeholder Q&As.
- **R-32 (Keyboard Accessibility)**: All controls must be navigable via `Tab`, activatable via `Enter`/`Space`, and dismissible via `Escape`.
- **R-33 (No Script Patching)**: Fix styles and structure in source files, never via ad-hoc client-side JavaScript DOM patches.
- **R-34 (Theme Completeness)**: Every theme shipped (light/dark) must be tested, readable, and fully styled.
- **R-35 (Verify Before Delivery)**: Test the built deliverable across viewports and interaction flows before declaring complete.
- **R-36 (No Fabricated Claims)**: Zero synthetic awards, fake partnerships, or false compliance badges.
- **R-37 (Design Direction Required)**: Settle brand/design direction before building. When none exists, state "draft without direction" and keep dials at 1/1/1.
- **R-38 (Honest Placeholders)**: Clearly demarcate temporary data with `[REAL DATA REQUIRED]`; never disguise fake values as final.

### Group 2: Purpose-Gate (Allowed Only With Explicit Purpose)
- **R-01 (Color & Gradients)**: No decorative gradients. Permitted only for functional loading shimmer, edge fade masks, or photo contrast overlays.
- **R-04 (Icons)**: Use icons only to reinforce semantic meaning, not as bullet-point wallpaper.
- **R-06 (Typography)**: Use design system typography scales; never mix ad-hoc fonts or fake terminal `>` styling.
- **R-07 (Backgrounds)**: Solid, purposeful surfaces. No floating ambient decorative blobs or abstract noise.
- **R-08 (Button Arrows)**: Arrows indicate navigation or flow; do not attach redundant `->` to every action button.
- **R-09 (Badges)**: Badges represent true operational states. Never attach pulsing animations to static statuses.
- **R-10 (Glassmorphism)**: Frosted blur (`backdrop-filter`) is restricted to the single sticky header over scrolling content. Banned on cards, modals, and popovers.
- **R-12 (Shadows)**: Elevation indicates layering hierarchy. No soft, floating ambient blur across flat cards.
- **R-13 (Glows)**: Colored glow halos (`box-shadow: 0 0 24px var(--accent)`) are strictly banned.
- **R-14 (Feature Cards)**: Card grids must convey unique data structures, not repetitive 3-column marketing blocks.
- **R-19 (Animations)**: Animations must communicate state transitions or live processes, never gratuitous loop decoration.
- **R-22 (Illustrations)**: Visual diagrams must depict real architectures or flows, not abstract stock artwork.

### Group 3: Quality Locks (Consistency & Integrity)
- **R-05 (Layout Structure)**: Content follows a structured grid with consistent rhythm and spacing.
- **R-11 (Border Radius)**: Radii derive from token scales (e.g. 6px, 10px, 14px). No oversized pill cards.
- **R-15 (Call to Action)**: CTAs state the exact user action in clear verbs.
- **R-16 (Buzzword Ban)**: Eliminate AI promotional clichés.
- **R-20 (Visual Identity)**: Consistent aesthetic vocabulary throughout the application.
- **R-21 (Dark Mode)**: Dark themes must maintain contrast, distinct surface depths, and crisp borders.
- **R-29 (Color Palette)**: Single primary accent accompanied by standard semantic status tokens (`success`, `warning`, `danger`).
- **R-30 (Product Originality)**: Solve the specific domain problem; do not mimic generic SaaS templates.
- **R-31 (Reasoned Decisions)**: Every rule exception must be explicitly justified in code or commit notes.

---

## 3. Domain Playbooks & References

The complete upstream rulebook and domain specifications are organized in `references/`:

### Domain A: Code Comments (`references/antislop-code.md`)
- **Scope Guardrail**: Governs comments and documentation only. **Never modify executable code, identifiers, imports, or control flow** during comment cleanup.
- **Decorative Separators**: Banned. Strip banner lines (`// =======================`, `/* ---------- */`, ASCII box headers).
- **Restating the Obvious**: Banned. Delete comments that echo syntax (`let count = 0 // Initialize count`).
- **Workflow Narration**: Banned. Delete step numbering (`// Step 1: parse input`, `// Step 2: process`).
- **Empty Generic Labels**: Banned. Strip vacuous labels (`// Main logic`, `// Helper function`).
- **Placeholder TODOs**: Replace or remove blind TODOs. Keep only actionable items with specific technical constraints.
- **Preserve Essential Notes**: Always preserve notes explaining architectural trade-offs, security invariants, concurrency models, protocol quirks, and non-obvious hardware/OS traps.

### Domain B: Copywriting & Content (`references/antislop-copywriting.md`)
- **Banned AI Vocabulary**: Strictly eliminate hollow promotional jargon:
  *unlock, elevate, empower, delve, showcase, testament, landscape, journey, robust, game-changer, next-level, seamless, cutting-edge, revolutionary, supercharge, unleash*.
- **Significance Inflation**: Replace grandiose claims ("a new era of repository safety") with direct functional statements ("automated nightly repository backups").
- **Unsubstantiated Proof**: Remove synthetic trust slogans unless backed by verifiable customer accounts.
- **Conversational Residue**: Strip assistant banter ("I hope this helps!", "As an AI model...") from documentation, UI strings, and commit messages.

### Domain C: UI & Visual Systems (`references/antislop-ui.md`)
- **Zero Untokenized Values**: All colors must use design system tokens (`var(--accent)`, `var(--bg-000)`, `var(--border-subtle)`). Never write raw hex or arbitrary `rgba()` in component styles.
- **Frosted Glass Dose Cap**: At most one translucent sticky top bar over scrolling content. Zero blur on modals, menus, inputs, or cards.
- **Grounded Philosophy**: Elements remain anchored in their layout plane. Zero vertical hover displacement (`translateY`).
- **Color Discipline**: Avoid arbitrary rainbow category colors. Status indicators use established semantic meanings only.

### Domain D: Layout & Mobile Responsiveness (`references/antislop-layoutmobile.md`)
- **Continuous Viewport Flow**: Test across 375px (mobile), 768px (tablet), 1024px (small desktop), and 1440px (wide). Never jump between two extreme states while neglecting the 600–1024px band.
- **Mobile First-Class Styling**: Mobile layout is designed intentionally, not patched as an afterthought media query.
- **Fluid Typography**: Sized with viewport scales (`clamp()`) or stepped breakpoints so headlines fit narrow viewports without clipping.
- **Viewport Height Safety**: Avoid `100vh` on mobile web layouts to prevent browser chrome toolbar clipping. Use `100dvh` or natural content flow.
- **Minimum Tap Targets**: Interactive controls must provide a minimum target area of 44×44px on mobile devices.

### Domain E: Human Usability & Accessibility (`references/antislop-human.md`)
- **Contrast Ratios**: Normal text must satisfy 4.5:1 against its background. Large text (18px+ or 14px bold) must satisfy 3.0:1.
- **Non-Text Elements**: Component boundaries and graphical status indicators must satisfy 3.0:1 against adjacent surfaces.
- **Verification**: Use `scripts/contrast-check.py` or MCP server `scripts/contrast-mcp.py` to calculate exact mathematical ratios.
- **Keyboard Navigation**: All controls are reachable via `Tab` and activated via `Enter` or `Space`. Dialogs must dismiss via `Escape`.
- **Focus Rings**: Never remove focus indicators (`outline: none`) without providing a visible high-contrast replacement.
- **Unrestricted Zoom**: Never set `user-scalable=no` or `maximum-scale=1.0` in viewport metadata.

#### Contrast Reference Table

| Pairing (text on background) | Ratio | Normal text (4.5) | Large text (3.0) |
|---|---|---|---|
| Black on white | 21.00 | Pass | Pass |
| White on black | 21.00 | Pass | Pass |
| White on #333333 | 12.63 | Pass | Pass |
| White on #666666 | 5.74 | Pass | Pass |
| #777777 on white | 4.48 | Fail | Pass |
| White on #888888 | 3.54 | Fail | Pass |
| White on #999999 | 2.85 | Fail | Fail |
| #555555 on black | 2.82 | Fail | Fail |

---

## 4. The 4-Block Delivery Gate

Before submitting code, opening a pull request, or declaring a task complete, verify each block:

1. **Block 1: Hard Gate**:
   - Zero fabricated claims, statistics, or customer proof.
   - Contrast passes WCAG AA on all shipped pairings.
   - Layout reflows cleanly without horizontal overflow down to 320px.
   - All interactive controls are keyboard navigable with visible focus states.
2. **Block 2: Purpose-Gate**:
   - Every gradient, shadow, badge, and icon serves an identified functional role.
   - Zero glowing neon box-shadow halos.
   - Glassmorphism confined to the allowed sticky top bar.
3. **Block 3: Craftsmanship & Quality**:
   - Zero hardcoded colors outside design system tokens.
   - Zero AI buzzwords in copy, UI headings, or documentation.
   - Code comments contain no decorative banners, emoji, or obvious restatements.
4. **Block 4: Verification**:
   - `scripts/check-anti-slop.sh` passes with zero un-allowlisted findings.
   - `scripts/contrast-check.py --selftest` passes.
