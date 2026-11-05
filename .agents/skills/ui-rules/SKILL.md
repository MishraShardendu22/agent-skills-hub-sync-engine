---
name: ui-rules
scope: generic
description: Frontend visual invariants for the dashboard and every app built on the Observatory design system: tokens over hardcoded values, library components over hand-styled markup, the status vocabulary, no hover levitation, no AI aesthetic bloat, device-driven theme with no toggle.
---

# UI Rules & Visual Engineering Standards

These rules apply to the dashboard app under `src/apps/` and to any app that installs the
Observatory design system ([`MishraShardendu22/observatory-ui`](https://github.com/MishraShardendu22/observatory-ui)):
`@mishrashardendu22/observatory-tokens` (CSS custom properties, a Tailwind v4 theme, a typed
object) and `@mishrashardendu22/observatory-ui` (React components and `styles.css`). The brand
book that explains the tokens lives with the design system; this skill is the engineering contract.
Taste and restraint on top of it (no decorative gradients, glass, pulses, emoji or hype copy) are
the `anti-slop` skill, checked by `scripts/check-anti-slop.sh` (or `make anti-slop-check`).

---

## 1. Rule: Tokens, never values

- Colour, radius, spacing, shadow and font stacks come from the tokens: `var(--accent)`,
  `var(--bg-100)`, `var(--radius-md)`, `var(--space-4)`. A hex, `rgb()` or px radius in a
  component or stylesheet is a defect unless it is in `tokens.json` itself.
- Grounds step up by lightness: `--bg-000` page, `--bg-100` cards and sidebar, `--bg-200` fills
  inside a card, `--bg-300` popovers. Never skip a step.
- Text is `--ink`, `--ink-secondary` or `--ink-muted`; every pair meets 4.5:1 on the grounds the
  token's `usage` note names, in both themes. `--ink-muted` never sits on `--bg-300` in dark.
- The one accent is amber: `--accent` as ink (kickers, links, active nav, icon tiles, focus ring),
  `--accent-fill` with `--ink-inverse` as the primary button fill. The old violet survives only as
  `--info` for the Running state.
- Charts use `chartColors`, `chartAxisProps`, `chartGridProps` and `chartTooltipStyle` from the
  ui package. Successful is the amber primary series; failed is `--chart-failed` (dark rust);
  skipped is `--chart-skipped`. No other colour appears in a chart.
- A subtle overlay is `color-mix(in srgb, var(--ink) 6%, transparent)`, never `rgba(255,255,255,…)`,
  so it follows the theme.

## 2. Rule: Components, not hand-styled markup

- Use the library: `Button`/`ButtonLink`/`IconButton`, `Card`/`CardHead`/`CardTitle`/`CardMeta`,
  `StatCard`/`StatStrip`, `PageHeader`/`Kicker`, `Badge`/`StatusBadge`/`Pill`, `Field`/`Input`/
  `Textarea`/`Select`/`Checkbox`/`Segmented`, `Table`/`TableWrap`, `List`/`ListRow`, `Steps`,
  `Notice`, `NavCard`, `EmptyState`/`ErrorState`/`LoadingState`/`LoadingPanel`/`Spinner`/`Skeleton`,
  `Dialog`, `Dropdown`, `Tabs`/`Tab`, `Pagination`, the `AppShell`/`Sidebar`/`TreeNode` family, `GitHubIcon`.
  An app keeps no UI primitives of its own: a missing piece is added to the library and released.
  For client navigation pass `component={Link}` to `ButtonLink`, `NavCard` and `ListRow`.
- Inline `style={{…}}` is for one-off layout (a gap, a max-width), never for colour, radius,
  font or shadow. A block of inline styles that recurs is a missing component: add it to the
  library, release, bump.
- Status is a fixed vocabulary and is never colour alone: Completed (`success`), Failed (`error`),
  Running (`running`), Degraded (`warning`), Skipped (`neutral`). `StatusBadge` maps the API's
  status words; a list row carries a check or an x beside the word.
- One `Button variant="primary"` per view, and it is the action the page exists for. One
  `Card glow` per view at most.
- Class names in `styles.css` (`.btn`, `.card`, `.stat-card`, `.badge-success`, `.tree-node.active`,
  `.table`, `.input`) exist so older markup keeps working; new markup uses the components.
- Dashboard-only styles (app shell, sidebar chrome, landing page, chat UI) live in
  `src/app/styles/app.css`, `ai.css` and `search.css`. Anything two apps would want goes into the
  design system instead.

## 3. Rule: Theme follows the device, with no toggle

`tokens.css` is dark by default and applies the light values under `prefers-color-scheme: light`
when the page sets no `data-theme`. There is no theme toggle, no theme provider and no stored
preference: a toggle needs a client component and a hydration-safe store for a choice the OS
already makes. To pin a page, set `<html data-theme="dark">`. Every new colour must therefore be
a token with both theme values, checked at 4.5:1.

## 4. Rule: Absolute ban on hover levitation

> [!CAUTION]
> **ZERO VERTICAL DISPLACEMENT ON HOVER**: Elements must NEVER move up or shift on hover.
> `hover:-translate-y-*`, `translateY(-…)` in a `:hover` rule, float or bounce are forbidden.

Hover changes colour, border or background only (`--border-strong`, `--bg-200`, `--accent`);
the one glow is `--shadow-glow` on a `NavCard`. Press is `scale(0.98)`. Transitions are 150 ms on
colour, border and background. Content reveals use `.reveal` with `.stagger-1` to `.stagger-5`, at
most five items. Everything respects `prefers-reduced-motion`.

`src/app/styles/hover-motion.test.ts` fails the build for any `:hover` rule with a `translate` and
any `hover:-translate-y-` utility.

## 5. Rule: Elimination of AI-generated aesthetic bloat

1. **No fake macOS window chrome**: no red/yellow/green dots on cards or modals.
2. **No decorative icon pollution**: no `Sparkles`, `Bot`, `Layers`, `Cpu`, `Wrench`, `ShieldCheck`
   beside headings. Icons are functional (Lucide at 16px in controls, 18px in navigation, 20px in
   icon tiles) and mark a state, a destination or an action. The product mark is `ObservatoryMark` from the library (one ink, `currentColor`); the GitHub mark is only for links to GitHub. Illustrations are the brand's orbit scenes, kept to the landing hero, a closing panel and a site's home; never behind data.
3. **No fake status lights or filler metrics**: numbers on a page are real numbers from the API,
   or the page shows nothing there.
4. **No gradients, no coloured left borders, no 28px radii**: cards are flat `--bg-100` on a 1px
   `--border` at `--radius-lg`; controls are `--radius-md`; badges are pills.
5. **No emoji, no exclamation marks, no "Oops"**: sentence case, one italic `<em>` per headline at
   most, errors that state what failed and the next action.

## 6. Rule: Layout discipline

- Every app page renders inside `.page` (a column with `--space-8` gaps) within `.app-main`
  (`--content-max` 1280px, 40px top, 64px bottom, `clamp(24px, 4vw, 48px)` gutter).
- A page starts with `PageHeader` (kicker, serif title, one-line subtitle, up to three actions),
  then a `.metric-grid.metric-grid--four` of `StatCard`s, then one wide card beside one narrow card
  (`.split-grid--wide`), then secondary cards.
- Grids: `.metric-grid--four` (2 columns under 960px, 1 under 640px), `--three`, `--two`, `--six`.
  Tables collapse into label/value cards under 640px when each `<td>` has a `data-label`.
- The public landing page (`src/app/(marketing)/page.tsx`) is the same system without the sidebar:
  a 56px pill nav, a hero, a preview frame showing one dated sample run (`src/content/sample-run.ts`;
  never live or invented numbers), four feature cards (plain `Card`s with `.landing-feature`: they
  open nothing, so they are not `NavCard`s), the pre-order section (pay buttons only once pre-orders
  are open: a payment link and a support email; otherwise a "not open yet" note with the waitlist
  form or a documentation link, never a dead end), `Steps` and a
  closing `Card variant="hero" glow`. The marketing pages are static (no `cookies()`/`headers()`,
  `revalidate` on the marketing layout). Calls to action go to the pre-order section or the docs
  site (`DOCS_URL`); never to the private repository (its URLs answer 404 to visitors) or into the
  app. It never claims what the product does not do (the source is proprietary-licensed, not
  "open source"; the product does not run on Vercel, Render or Neon).

## 7. Automated verification

`pnpm run lint` (Biome), `pnpm exec tsc --noEmit`, `pnpm test` (includes the hover-motion test)
and `pnpm run build` run in the pre-push hook and in CI (the pre-commit hook runs only the fast checks). A change to the design system itself is
made in the library repository; its merge publishes the packages and opens the upgrade pull request
in this repository automatically (exact versions, regenerated lockfiles), so the two packages are
never bumped by hand in a feature branch.
