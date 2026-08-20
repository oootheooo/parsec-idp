# Parse Design System

Parse uses an editorial, product-first interface inspired by Exa's restraint: generous white space, serif display type, near-black primary actions, fine neutral borders, and compact interactive surfaces. It is an interpretation for document operations, not a copy of Exa's brand. This system governs product structure and placement—not only styling.

## Principles

1. **Quiet confidence.** Most surfaces are white, borders are fine, and shadows are barely visible. Color communicates meaning rather than decoration.
2. **The document is the hero.** Controls stay compact so source files and extracted data receive the visual emphasis.
3. **Progressive density.** Marketing/authentication screens can breathe; operational tables and review tools stay dense and scannable.
4. **One accent.** Pine green is used for focus, progress, links, and positive states. Primary commitment actions use near-black.
5. **Motion explains state.** Entrance and scanning motion are short and subtle, and always respect reduced-motion settings.
6. **Product structure before cards.** Navigation, hierarchy, tables, and whitespace organize the interface. Do not create a grid of interchangeable rounded cards to solve every layout problem.

## Brand identity

- Use the text wordmark **Parse** with the optional qualifier **by Handl**.
- Parse has no approved symbol or logo yet. Do not use a `P` tile, letter avatar, generated mark, or placeholder logo anywhere in the product.
- Until a permanent identity is approved, the wordmark must remain plain text and must not be turned into a pseudo-logo with a box, circle, gradient, or badge.

## Application framework

The desktop product uses a single horizontal application rail. It contains, in order:

1. Parse wordmark at the left;
2. primary product navigation in the center-left;
3. workspace selector and global upload action at the right;
4. restrained account information and logout control at the far right.

Do not reintroduce a persistent dashboard sidebar. A sidebar may only appear inside a feature when the content itself requires a master/detail relationship, such as source document versus extracted fields.

The application rail is 64px high and remains visible while scrolling. Product content sits inside a centered 1280px frame. Wide operational views such as document review may deliberately break out of that frame.

On mobile, the wordmark and global actions remain in the header. The six primary destinations move into a fixed bottom rail; there is no hamburger drawer for core navigation.

## Page anatomy

Standard index and overview pages follow this vertical order:

1. **Page header:** eyebrow, editorial title, short explanation, and one page-level action. It ends with a full-width divider.
2. **Toolbar:** search and filters on an unboxed horizontal rail with top and bottom dividers.
3. **Primary content:** table, structured list, or intentionally asymmetric grid.
4. **Secondary detail:** only when it helps the primary task; it should not compete with the main surface.

Use a 12-column mental model. Primary operational content normally occupies 8 columns and supporting context 4 columns. Forms use a narrower 720–960px reading width. Do not center narrow cards inside large empty canvases unless the screen is authentication or a single-purpose task.

Empty states are horizontal product messages: owned symbol, explanation, then action. Avoid decorative illustrations, dotted boxes, giant icons, and nested rounded panels.

## Foundations

- Display type: Georgia / Times fallback, regular weight, tight tracking.
- UI type: Inter when available, then Avenir Next / Segoe UI / system sans.
- Ink: `#181f1c`
- Pine: `#3d6f5b`
- Deep pine: `#2a5243`
- Sage mist: `#e8f2ed`
- Paper: `#f9faf8`
- Line: `#e1e5e1`
- Radius: 8px controls, 12px panels, 18px feature surfaces.
- Spacing: 4px base rhythm; typical panel padding is 20–24px.

The canonical values live as CSS variables in `src/index.css` and are mapped into Tailwind in `tailwind.config.js`. Do not add arbitrary brand hex values inside components.

## Components

- `.page-shell`, `.page-kicker`, `.page-title`, `.page-description`: page hierarchy.
- `.page-header`: standard title/action placement with a structural divider.
- `.page-toolbar`: unboxed search/filter rail.
- `.btn-primary`: near-black primary commitment action.
- `.btn-brand`: green progress/positive action.
- `.btn-secondary`, `.btn-ghost`, `.btn-icon`: decreasing visual emphasis.
- `.input`, `.label`, `.help-text`: form controls and help copy.
- `.card`, `.card-interactive`: static and clickable surfaces.
- `.section-header`, `.section-title`: panel composition.
- `.tabs`, `.tab`, `.tab-active`: tab navigation.
- `.data-table`: operational tables.
- `.notice-success`, `.notice-warning`, `.notice-danger`: feedback.

## Icon language

- Product-level icons come from `src/components/ProductIcons.tsx`. They are owned, geometric SVGs with a consistent 1.45px stroke, open corners, and minimal rounded detail.
- The owned set is required for primary navigation, product areas, empty states, and global actions.
- General-purpose icons may be used only for literal controls such as edit, copy, delete, zoom, save, or back.
- Do not mix icon weights. General-purpose control icons should visually match the thin product stroke.
- Do not place every icon inside a tinted rounded square. An icon container is reserved for a state that genuinely needs a target or boundary.
- Icons support labels; they do not replace labels for unfamiliar product actions.

## Motion system

Motion confirms an interaction or preserves orientation. It is never decoration.

### Timing

- Fast — `110ms`: button press, icon control, table-row feedback.
- Standard — `180ms`: hover elevation, tab underline, focus treatment.
- Slow — `260ms`: page changes, notices, status changes, evidence expansion.
- Use `--parse-ease` for direct manipulation and `--parse-ease-out` for elements entering or settling.

### Interaction patterns

- Buttons rise by no more than 1px on hover and compress to 98.5% while pressed.
- Interactive cards rise by no more than 2px. Static cards do not move.
- Navigation and tab selection use a short underline expansion rather than moving the whole control.
- Notices and changed statuses fade in with 2–3px of movement.
- PDF page changes crossfade with a 4px horizontal offset so the reader retains spatial context.
- Evidence details use a short vertical reveal. Field cards themselves remain stable.
- Focus animation changes border and shadow only; form fields must not resize or move.

### Restrictions

- No bouncing, elastic easing, large scaling, rotating decoration, parallax, continuous floating, cursor-following, or scroll-triggered spectacle.
- Do not stagger lists or animate every row on initial load.
- Continuous animation is reserved for active processing or loading states.
- Animations must not delay navigation, submission, review, or data entry.
- Every animation and transition must collapse under `prefers-reduced-motion: reduce`.

## Usage rules

- Use one primary action per page region.
- Prefer borders and spacing to heavy shadows.
- Do not use gradients on buttons or cards. Ambient background gradients are allowed only as low-contrast atmosphere.
- Keep body copy at 14px or larger; metadata may use 11–12px.
- Icons are 16–20px and inherit text color. Put standalone feature icons in `.icon-tile`.
- Use green for selected, focused, progressing, or successful states—not for every icon.
- Prefer navigation underlines, dividers, and whitespace over filled navigation pills.
- Do not add a left application sidebar or generic statistic-card mosaic.
- New screens must support keyboard focus and reduced motion.

## Product copy

- Authenticated screens use direct, functional language. Titles name the page or action: `Overview`, `Documents`, `Upload document`, `New processor`.
- Do not use marketing headlines, slogans, benefit statements, or conversational filler inside the product.
- Avoid phrases such as “at a glance,” “made simple,” “you can trust,” “powerful,” “seamless,” “everything in one place,” and similar promotional copy.
- Do not explain what an obvious page is for beneath its title. Descriptions are allowed only when they communicate required behavior, security consequences, processing choices, or technical constraints.
- Empty states state the condition and the next action: `No documents` and `Upload document`.
- Eyebrows are reserved for real scope or state, such as `Last 30 days`; never use them as decorative category labels.

## Page templates

- **Index:** divided page heading + right-aligned action, unboxed toolbar, table or structured collection.
- **Detail:** status + title + action cluster, then a 2:1 content/details grid.
- **Editor:** back link, title + save actions, message notices, one structured editor panel.
- **Review:** fixed workspace header, dark document canvas, white evidence panel.
