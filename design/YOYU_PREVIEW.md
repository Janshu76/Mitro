# Yoyu-inspired Mitro preview

Reference: [yoyu.design](https://yoyu.design/), visually inspected on 31 October 2026.

New page: `mitro-yoyu.html`; new theme: `yoyu.css`. Open http://127.0.0.1:8001/design/mitro-yoyu.html using the existing optional `design.preview` server. The previous gallery remains unchanged; the new page links back to it.

The reference's graph-paper background, pixel artwork, oversized central identity, fine navigation, and rectangular black actions inform this variant. It uses original inline SVG illustrations of a document, a reviewer, and a code monitor, with a restrained teal accent. There are no borrowed third-party characters, tracking scripts, image downloads, or font dependencies. Decorative motion does not imply work is running.

The working screens retain the original forms and controls, with square borders, clear typography, and restrained graph-paper styling. Existing API requests and the complete Optimus-variant functional script are preserved. The user-requested reference style overrides the earlier provisional prohibition on centered overview layouts for this variant only.

## Verification

- All 67 baseline interface IDs retained without duplicates; functional script passes `node --check`.
- All previously existing design files, original UI, and backend source verified unchanged by the builder.
- Browser loads 11 library documents from the real local API.
- Document navigation, loading 9 IRACP clauses, filtering `36C` to 2 matching chunks, and opening the obligation form from a quote checked.
- Overview, Documents, and Clauses screens checked at 320px with no page overflow (305px content width plus scrollbar).
- Desktop and mobile layout inspected. Screenshot saved as `mitro-yoyu-preview.png`.

Build with `.venv/Scripts/python.exe design/build_yoyu_preview.py`. This creates only the new Yoyu HTML, validates its script, and asserts that previously existing files remain unchanged. It does not update existing galleries or earlier previews.

End-to-end uploads, external source checks, configured AI drafting, approvals, registration, scans, and successful build/download were not repeated for this visual variant. They retain the existing handlers; the previously documented local partial-build conflict is unchanged. Use the local server for API behavior; opening the HTML directly is a visual-only view.

## Reference-inspired motion

Added at the user's request: `yoyu-motion.css` and `yoyu-motion.js`, loaded only by this variant. The builder includes both without changing the functional application script or other preview styles.

- Sixteen background sprites: small roaming pixel characters, faint character silhouettes, and drifting pixel sparkles. The decorative layer is inert, hidden from assistive technology, and cannot intercept clicks.
- Stepped bob/tilt loops on the large pixel illustrations, small glints, bracket nods, arrow nudges, and workflow markers. Evidence text and editable controls do not loop or move while being read/edited.
- Staggered viewport reveals for sections, cards, headings, form fields, library rows, clauses, obligations, findings, and code panels. Dynamically loaded results are observed automatically. Content remains visible if scripting or observer support is unavailable.
- Button hover/press feedback, card hover lift, focus styling, and summary/badge interactions.
- A persistent Motion on/off switch in the header disables decorative motion across the page. System reduced-motion preferences take priority. Animations pause when the document is hidden. Background sprites use only transform and opacity for movement, with fewer sprites on mobile.

Browser checked: roaming sprite positions change over time; 16 sprites present; the motion switch updates state and persists off after reload; switching back on works; 11 document rows load; working sections receive reveal classes. Mobile and clause checks are recorded in the chat. Prior preview files and the backend remain unchanged.
