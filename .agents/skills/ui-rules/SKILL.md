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
  component or stylesheet is a defect unless it is in `tokens.json` itself. One exception:
  `src/app/styles/marketing.css` defines the public pages' type scale, widths, grid, tap target
  and anchor offset in px until observatory-tokens has them (the list to upstream is in
  `docs/DESIGN_SYSTEM_RELEASES.md`); it still adds no colour or radius.
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
- The public pages' browser JavaScript has a budget (`lighthouserc.json`, 120 KB of script), and
  React and Next.js take about 108 KB brotli of it. Import components from the package root,
  `@mishrashardendu22/observatory-ui`: 0.3.0 has no per-component entry points, and the build keeps
  only the components a page imports. The public pages, the analytics settings panel and the root
  `not-found.tsx` draw icons from `src/components/icons.tsx` (inline SVG with lucide's paths and
  `lucide lucide-<name>` classes), never from `lucide-react`: lucide-react 1.67 marks its `Icon`
  "use client", so any lucide icon, even one a server component draws, ships `Icon` (about 1 KB
  brotli) to every page. An icon those pages need is added to `icons.tsx` with a case in
  `icons.test.ts`; the signed-in app keeps `lucide-react`. A client component still takes its icons
  as props from the server component above it where it can (`MobileMenu`'s `openIcon` and
  `closeIcon`). UI that appears only after a click loads with `React.lazy` when it is first needed
  (`ConsentPanel`): the parent handles Escape from the moment it opens, a failed import resolves
  to a small panel that says so (never a throw, which reaches Next.js's error page and replaces the
  page), and the button that opens it starts the fetch on hover and focus. Do not add
  `next/dynamic` to a public page, its loader adds about 2 KB brotli to every page. Browser code on
  every page imports `src/config/analytics-env.ts`, not `src/config/env.ts`.
  `src/app/public-js.test.ts` checks the imports behind these rules.
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
- Dashboard-only styles (app shell, sidebar chrome, chat UI) live in `src/app/styles/app.css`,
  `ai.css` and `search.css`; the public pages (site bar, home page, `/pricing`, legal hub,
  footer) and their design layer live in `marketing.css`. Anything two apps would want goes into
  the design system instead.

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
   icon tiles) and mark a state, a destination or an action. The product mark is `ObservatoryMark`
   from the library (one ink, `currentColor`); the GitHub mark is only for links to GitHub.
   Illustrations are the brand's orbit scenes, kept to the docs and design sites' home pages and the
   social card; never behind data. The dashboard's public pages show the product instead (a recorded
   run, real bundles, real commands).
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
- The public home page (`src/app/(marketing)/page.tsx`) is the same system without the sidebar,
  and every line and number on it comes from `src/content/landing.ts`, where each figure was read
  from a real run (never estimated; change one only by running the thing again). Under the
  site bar it has five parts, each with one dense block, split by 1px rules:
  1. The hero: the h1 (`display-1`), the lead, `HeroActions` (the one action this build offers
     in place: the waitlist form when it works, the pay buttons when pre-orders open, else
     "Pricing and FAQ" to `/pricing`; then the docs as a text link), the founding terms in one
     `small` line, and `SampleRunCard`, titled "Sample run 29 · 20 September 2026": its totals
     and its log lines word for word, server-rendered, nothing counting up, no window dots or
     prompt. That worker wrote tar.gz snapshots before bundles shipped, so the run is
     "archived", never "bundled", and its caption says so. The LCP element is hero text (the h1
     at desktop widths, the lead on phones, where it is the larger block); no image anywhere on
     the page.
  2. `#features`: four facts as a `<dl>` (5 columns) beside a table of six real bundles
     (7 columns): branches, commits, size, SHA-256 prefix.
  3. `#how`, whose h2 is `#restore` (both land on the heading below the site bar; the empty
     `#how-it-works` keeps the section's old id for shared links): the restore commands,
     verified against a real bundle, with `CopyButton` (one command a line, never wrapped: a
     long line scrolls and the block takes focus), and what the worker needs, beside the failure
     table.
  4. `#preorder`, the price band (`PreorderSection.tsx`, at most 200px tall on desktop: the
     founding price, the three guarantee lines and a button to `/pricing`). It never repeats
     the hero's waitlist form or pay buttons: a page shows each once, so a `preorder_clicked`
     from `/` always comes from the hero.
  5. `#shipped`: dated product changes from merged pull requests, heading beside the list from
     1024px.
  Headings are two-tone (`.home-section__aside`): the claim in `--ink`, the rest in
  `--ink-secondary`; no uppercase eyebrows, no icon beside a heading, no closing card. Code,
  file names and settings in the copy are in backticks and render through `CodeText`. On phones
  the bundle table is two lines a row between 1px rules (`.phone-unit` adds the units the column
  heads gave; a third line only at 320px), each failure a plain row titled by the failure, and
  a repository's line in the run card shows its time and name (the repeated message is read out
  but not shown). `home.spec.ts` holds the page at its measured length (live build 2998px at
  1440px, 5352px at 375px; the brief's 375px target of 4200px is not met). The site bar holds
  How it works, Pricing and Docs (only while the server setting `DOCS_URL` is set) from 960px; below, a labelled Menu button (`MobileMenu.tsx`:
  `aria-expanded`; Escape, a click outside, a click on one of its links or focus leaving it
  closes it) opens them in a sheet, and below 640px the outline button moves there too. The
  marketing pages render on each request (`dynamic = "force-dynamic"` on the marketing layout:
  `APP_URL` and `DOCS_URL` are the serving machine's) and read no cookie or header. Calls to action go to the pre-order section, `/pricing` or the docs site
  (`DOCS_URL`); never to the private repository (its URLs answer 404 to visitors) or into the
  app. It never claims what the product does not do (the source is proprietary-licensed, not
  "open source"; the server runs on one self-hosted machine, not on a cloud platform).

- The public pages share one design layer, `src/app/styles/marketing.css`, scoped to `.landing`
  (the marketing layout's wrapper) so the app is untouched. Type comes from its scale, set with
  the `.type-*` classes or `font: <weight> var(--type-*) var(--font-*)`: `display-1` (home h1,
  64/66 on desktop, 42/44 on phones), `display-2` (inner-page h1), `heading` (h2), `price`,
  `title` (h3 and card titles), `lead`, `body` (16/26), `small` (14/22, the floor for readable
  text), `code` and `caption` (mono only). The serif is for h1 and h2 at 28px and up, with
  `font-synthesis: none`; h3 and smaller are Inter 600 on the `title` step unless a block sets a
  smaller step. Widths and gaps are its variables: a
  1200px container (`.landing__inner`), 12 columns of 74px with 24px gutters (`.layout-grid`,
  8 on tablets and 4 on phones; a child sets `--span`), a 680px prose measure, 44px touch targets
  on phones. Breakpoints are 640px and 1024px. It adds no colour: the tokens of §1 only.
- `/pricing` (`src/app/(marketing)/pricing/page.tsx`) has one plan and no tiers, monthly toggle or
  "most popular" badge. The header (`display-2` h1, the product model in one line, the currency
  buttons) sits beside the plan card from 1024px (`--plan-card-max` 560px, the page 1080px), the
  card before the limits on phones. Both currencies are in the HTML: `CurrencySwap` puts them in one
  grid cell and marketing.css hides the one that `data-currency` on `<html>` does not name, with
  `visibility`, so a switch moves nothing (CLS 0). The root layout's head script (`CURRENCY_SCRIPT`
  in `src/lib/currency.ts`) sets that attribute before first paint from the stored choice or a guess
  from the time zone and language, never a geo header, so a visitor outside India never sees the
  rupee price first; `CurrencyScope` (the one client island) keeps the buttons in step and changes
  the attribute on a click. `currency.test.ts` runs the script against `browserCurrency()`. "What
  you get" is two lists side by side from 768px, Works today and Planned for launch, each under its
  icon and word, not a table. The nav marks Pricing with `aria-current` there and its button leads
  to the docs (`current="/pricing"`). Table heads and the phone labels are the `small` step in
  sentence case, and hyphenated terms stay on one line (`KeepHyphenated`, a nowrap span; the text
  keeps its plain hyphen). The card shows the action `PreorderAction` gives (pay buttons while open,
  with the waitlist under them when it is on; the waitlist as the primary button while closed; else
  a documentation link) and never a struck-through price or a places-left counter until the standard
  price and the payment page's stock count exist. The guarantee lines come from
  `PREORDER_GUARANTEES` in `src/content/preorder.ts`, which `/refund` renders too, and the FAQ, the
  limits and the dated competitor prices from `src/content/pricing.ts`; its FAQPage JSON-LD repeats
  the visible questions word for word. A status is an icon and a word, not a `Badge` (the light
  theme's success badge is under 4.5:1).
- A new public page is listed in four places: `PUBLIC_PAGES` in `src/content/site.ts` (the
  sitemap, `llms.txt` and the metadata test read it), `PUBLIC_PATHS` in `src/lib/auth/gate.ts`
  (else the login gate sends it to `/signin`), `PUBLIC_PATHS` in `src/lib/analytics/privacy.ts`
  (else replay masks it and records it like an app page) and `PAGES` in
  `scripts/lighthouse-dashboard.sh`. `src/content/public-pages.test.ts` fails until the gate and
  the privacy rules list every `PUBLIC_PAGES` path.
- The company and policy pages (`/about`, `/contact`, `/terms`, `/privacy`, `/refund`) use
  `LegalPage` (`src/components/marketing/LegalPage.tsx`): from 1024px a 240px sticky index (the
  hub's pages in two groups from `LEGAL_HUB`, then the page's sections), a 48px gap and a 720px
  article, on the container's left edge like the nav and the footer; below 1024px the index is a
  `<details>` above the article, sections first, and both keep the 720px measure. Each section is a
  `LegalSection`, whose h2 gets an id from its title without the number, so a renumbering keeps old
  links. A policy opens with a three-to-five-line summary that only repeats its text, and ends with
  its date and links to the other policies. The legal h2 is the `title` step in Inter 600, not the
  serif. `/delivery` is the `#delivery` section of `/refund` (307 in `next.config.ts`, temporary
  until Razorpay accepts the anchor), and the footer names it "Refunds and delivery". A page with
  subsections keeps one name per thing across them (`/refund`: h2 Refunds and cancellation and h2
  Delivery, each with the h3s Founding pre-orders and Annual plans after launch). The footer is
  rendered once, by the marketing layout after `<main>`, and sits at the bottom of a short page; it
  has two link groups (Product; Company and legal, ending with Analytics settings), side by side on
  phones with 44px-tall links.

## 7. Automated verification

`pnpm run lint` (Biome), `pnpm exec tsc --noEmit`, `pnpm test` (includes the hover-motion test)
and `pnpm run build` run in the pre-push hook and in CI (the pre-commit hook runs only the fast checks). A change to the design system itself is
made in the library repository; its merge publishes the packages and opens the upgrade pull request
in this repository automatically (exact versions, regenerated lockfiles), so the two packages are
never bumped by hand in a feature branch.
