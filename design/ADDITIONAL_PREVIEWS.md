# Four additional Mitro previews

These are new, separate HTML designs. The original UI, earlier overview concept, Optimus HTML/CSS, original variant builder, and API source remain unchanged. All new pages use the optional existing `design.preview` server and the same local demo database.

Open the comparison gallery at http://127.0.0.1:8001/design/previews.html.

If needed, start the preview from the Mitro project root:

```powershell
.venv/Scripts/python.exe -m uvicorn design.preview:app --host 127.0.0.1 --port 8001
```

| Preview | Reference | Direction | Local path |
| --- | --- | --- | --- |
| Technical dossier | [Christen Dijoux](https://christendijoux.com/) | Dark monochrome, technical labels, dithered geometry, oversized typography | `mitro-christen.html` |
| Editorial engineering | [Mecha](https://mecha-xyz.webflow.io/) | Airy asymmetric composition, wireframe mark, editorial serif headline, burgundy actions | `mitro-mecha.html` |
| Evidence control room | [Layers of Time](https://layersoftime.studio/) | Dark surfaces, luminous structural motif, cue-based sequence, muted rose accent | `mitro-layers.html` |
| Both sides of the rule | [Dev in the Hood](https://devinthehood.com/) | Warm source/document side against a dark engineering side; red and amber references | `mitro-hood.html` |

All four references were visually inspected in the browser on 31 October 2026. These are adaptations of their visual language, with original Mitro text and CSS/SVG illustrations. No third-party portraits, logos, screenshots, scripts, copied claims, or tracking are embedded in the working variants. Reference links open separately. The gallery uses screenshots of the new Mitro previews.

## Design decisions

The explicit request to follow these references overrides earlier provisional typography and palette restrictions for the new variants only. Mecha uses a system serif for its editorial overview; working review forms remain sans-serif. The split variant uses the reference's red/amber relationship in its illustrated overview. Existing UI tokens are not changed.

`preview-core.css` contains shared working-screen styles loaded only by these four new pages. Each loads its own theme stylesheet: `christen.css`, `mecha.css`, `layers.css`, or `hood.css`. `gallery.css` styles the new gallery only. No new page depends on `optimus.css`.

Rebuild the new HTML and gallery using `.venv/Scripts/python.exe design/build_more_previews.py`. The builder reads the baseline HTML and reuses the first preview's existing functional script. It asserts that all original interface IDs are retained, checks the script with Node, and verifies protected source/design files have not changed. It does not regenerate or overwrite previous variants. Gallery images are saved separately during browser inspection.

## Validation performed

- All 67 original element IDs retained in each new HTML file, without duplicate IDs.
- The complete functional script is identical to the existing Optimus variant, including its three variant-only behavior corrections. `node --check` passes.
- Each preview loads the real 11-document library. Document navigation and the IRACP document's 9 extracted clause chunks work in each variant. Filtering for `36C` shows 2 matching chunks in every variant.
- Selecting a clause quote opens the obligation form in the Layers variant.
- A Lendwise scan in the Layers variant returned 20 files and 15 candidate findings. JSON and code-preview modes were visibly available. This created one normal local scan record.
- Desktop screenshots inspected and saved for all four variants.
- At 320px, overview, Documents, and loaded Clauses screens in all four variants have no horizontal page overflow. The browser reports a 305px page width within its 320px viewport, allowing for the scrollbar.
- The gallery loads all four preview screenshots and links to the four new pages. It also links to the unchanged original UI, previous concept, and Optimus preview.
- Original UI, Optimus HTML/CSS, earlier concept, previous builder, and API source verified byte-for-byte unchanged.

## Verification limits

These are additional visual variants with preserved handlers, not a new backend implementation. Upload, source refresh, AI drafting, reviewer approval, repository registration, and successful patch build/ZIP download were not repeated for every theme. The previously documented local partial-build artifact collision remains a backend/demo-data limitation; this task does not alter those artifacts. Illustrative hero diagrams and pseudo-code do not represent running jobs or live results. Actual working controls use the original local API and perform their normal data operations.
