# Mitro redesign preview

`mitro-optimus.html` is a separate working HTML variant inspired by the user-supplied [Optimus reference](https://v0-optimus-delta.vercel.app/). The existing `web/index.html` and `ui-overview.html` are unchanged.

Run from the Mitro project root:

```powershell
.venv/Scripts/python.exe -m uvicorn design.preview:app --host 127.0.0.1 --port 8001
```

Open http://127.0.0.1:8001/design/mitro-optimus.html. The optional wrapper serves design assets and forwards the original application, including its API. `/` continues to show the original UI. Use this local server for working controls; opening the HTML directly is a visual preview only. Requests use the project's existing local demo database.

The stylesheet is `optimus.css`. To regenerate the HTML from the original functional baseline, run `.venv/Scripts/python.exe design/build_variant.py`.

## Verification — 31 October 2026

- All 67 original element IDs retained; no duplicate IDs; generated JavaScript passes `node --check`.
- Browser loaded 11 real library documents, source statuses, repositories, and obligation lists through the existing API.
- Navigation, cross-view links, same-document comparison validation, clause loading, and clause filtering checked.
- DLG paragraph 36C generated a real draft with quote, provenance, rationale, expected behavior, and diff. This test created draft proposal records in the local demo database.
- Lendwise scan completed: 20 files and 15 candidates. Readable, JSON, and code-preview result modes checked. The scan created its normal local scan record.
- Separate-copy build reached the backend and displayed its 409 partial-build conflict for proposal 1. Existing `data/phase3/proposal-1` artifacts were preserved. Successful build, test execution, and ZIP download were not verified during this redesign; this is a pre-existing local artifact/database collision, not a change to the backend.
- Desktop and 390px mobile visuals inspected. At 320px, overview, document screen, and loaded clause/proposal evidence had no page overflow after adding wrapping for long source hashes.
- The original API and UI have no source changes. All original event handlers are retained, with variant-only corrections for candidate-form expansion, visible impact JSON, and rendering clause-load errors as text.

Not exercised end to end: new uploads, external source checks, configured AI provider, reviewer approval, repository registration, successful build/download, or exhaustive keyboard/contrast checks. Their forms and API connections remain in the variant; do not treat this report as full regression certification.
