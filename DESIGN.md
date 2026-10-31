# Design System: Mitro

## Visual Direction

Use a bold, dark technology-marketing style inspired by the supplied reference: black canvas, huge condensed white headlines with periwinkle emphasis, royal-blue pill actions, light-blue flat vector artwork, and restrained network-line decoration. The tone is confident and clear while keeping Mitro's claims careful and evidence-based. The public landing page leads into the existing local review workbench.

## Color Tokens

- **Black Canvas** `#000000` — Page background.
- **White Text** `#FFFFFF` — Main headings and high-contrast copy.
- **Periwinkle Accent** `#7B9FE0` — Second headline line, highlights, and focus outline.
- **Royal Pill** `#2D47A3` — Primary buttons, topic links, and pill navigation.
- **Royal Hover** `#3A58C4` — Hover/active fill for pill actions.
- **Sky Blue** `#A5D0F3` — Illustration shapes and network nodes.
- **Paper Card** `#E8ECFA` — Document and clause previews where dark text is required.
- **Navy Ink** `#25243A` — Illustration outlines and text on paper surfaces.
- **Quiet Line** `rgba(255,255,255,0.18)` — Network geometry and dark-panel borders.
- **Soft Orange** `#F59E6C` — Small warning indicators and illustration details only.
- **Dark Panel** `#0A0A12` — Workbench cards and navigation surfaces.

## Typography

- **Display:** Bold condensed grotesque, preferring `Archivo Narrow` or `Barlow Condensed`, with local `Arial Narrow`/Impact fallbacks; tight tracking and compact line-height.
- **Body and controls:** `Inter`, then system sans-serif fallbacks; use high contrast and relaxed line spacing.
- **Code and provenance:** `Consolas` or system monospace.
- Hero headlines scale with `clamp(3rem, 9vw, 7.5rem)`. Pill labels use bold condensed text. At mobile widths, headlines may wrap naturally without clipping.

## Shape & Components

- **Pills:** Fully rounded, royal-blue fill, white condensed label, 44px minimum touch target. Hover lifts 2px and lightens the blue.
- **Panels:** `#0A0A12`, 1px quiet-line border, 16px radius. Use paper-colored surfaces only for source quotations, document previews, and illustration screens.
- **Inputs:** Dark fill with visible labels, light text, clear borders, and a 2px periwinkle focus outline.
- **Status:** Include descriptive text alongside any color marker. Amber/orange is reserved for review-needed states; green/red diff colors must remain readable on dark surfaces.
- **Diffs and code:** Monospace panels with distinct added/removed line colors and internal overflow handling.

## Landing Page Composition

The landing page is a centered scrolling composition with a two-line headline (“Turn Regulation / Into Engineering!”), one factual supporting line, five flexible pill links, a responsive inline SVG illustration, a concise workflow tagline, and two clear actions. The illustration depicts source evidence moving through human review into candidate engineering impact. Add a faint cropped geodesic sphere near the headline and a constellation network behind the lower content. The drawing is decorative but has an accessible label.

The main action opens the workbench. The RBI/2025-26/210 action opens the existing bootstrap and clause-review flow. The topic pills deep-link to the corresponding existing workbench sections. All sample activity is labeled illustrative; do not invent live counts, testimonials, compliance scores, or legal conclusions.

## Workbench

Keep the existing single-page views and API-driven behavior. Restyle navigation as royal-blue pills, content panels as dark bordered surfaces, controls as dark fields, and document excerpts as readable paper cards. Preserve the document upload and source checks, clause extraction and obligation review, candidate code scan, and the two supported Phase 3 patch scenarios. Phase 3 must clearly state that proposed changes are prepared in a separate Lendwise copy and never alter the original repository.

## Responsive, Accessibility & Motion

Support 375px screens without horizontal page overflow. Let pill links wrap, scale SVG artwork fluidly, and stack workbench columns below 700px. Maintain at least 4.5:1 contrast for body text, visible keyboard focus, semantic headings, and descriptive SVG labeling. Honor `prefers-reduced-motion`; the network decoration may drift subtly only when motion is allowed. Avoid animating layout dimensions.

## Trust Language

Mitro is a local demo platform. Lendwise is fictional. Scan results are candidate locations for human review, not confirmed findings. Mitro is not legal advice, a compliance certification, or a determination that a regulation was violated. Preserve RBI/MeitY source citations and provenance through every workflow stage.

## Avoid

- Neon gradients, glowing accents, decorative gradient text, or motion that distracts from evidence.
- Misleading legal certainty, fabricated status metrics, or unlabeled illustrative data.
- Treating candidate code locations as confirmed regulatory findings.
- Decorative color-only states, inaccessible focus, clipped text, or mobile horizontal scrolling.
- Modifying backend logic, database schema, supported patch cases, or Lendwise source code as part of UI work.

## Alternate Exploration Pages

The separate concept pages remain available for comparison through `web/theme-options.html`: Forest Clinic, Midnight Editorial, Amber Ledger, and Mineral Blue. The active application identity is the black/periwinkle system above.
