# Mitro demo walkthrough

This walkthrough uses only Mitro's included regulatory corpus and the fictional Lendwise app. It does not connect to a real lender or change source code.

## Current Phase 1, 2, and 3 demo capabilities

- **Phase 1:** document upload and extraction, version comparison, on-demand official source checks, source hashes, rule-based clause candidates, and optional Ollama or Sarvam obligation drafts. Obligations stay proposed until a reviewer approves them.
- **Phase 2:** read-only multi-language pattern scans and a Python code graph for Lendwise or another registered local folder. Candidate locations require human review.
- **Phase 3:** select a regulatory clause and ask for a code change directly, without creating an obligation first. The demo supports Digital Lending paragraph 10.1 (legacy-import consent) and IRACP Amendment paragraph 36C (reduced DLG cover). Inspect the diff, then create a separate edited copy and run its generated regression test. Download the copy as a ZIP.
- **No GitHub publishing:** this build does not write code, create pull requests, or push to GitHub.

AI drafting is optional. Copy `.env.example` to `.env`, set up a running Ollama model (default `qwen2.5`) or a Sarvam API key, and restart the server. Repository code is never sent to the AI provider.

## Start the local demo

From the Mitro project folder in VS Code's PowerShell terminal:

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn mitro.api.app:app --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000/>. Leave the terminal open while presenting.

## Five-minute Phase 3 walkthrough

1. **Open the RBI DLG amendment.** In the document library, select “RBI NBFC IRACP Amendment Directions, 2026 - DLG provisioning,” then open clause 36C. The selected amendment is also in the official RBI notification page referenced in the library.
2. **Request a code change from the clause.** Select **Suggest code change**. Mitro explains the DLG cover adjustment, points to `app/services/provisioning.py`, and displays the proposed diff. No obligation needs to be created first.
3. **Build the review copy.** Inspect the expected behavior, then select **Create separate edited copy and run test**. Mitro applies the patch in a separate Lendwise copy and runs the generated deterministic regression checks. The original `targets/lendwise` remains unchanged.
4. **Download and inspect.** Select **Download edited Lendwise copy (.zip)**. The ZIP contains the changed source, generated test, and synthetic demo code.
5. **Show the consent case if time permits.** Open the RBI Guidelines on Digital Lending, paragraph 10.1 and select **Suggest code change**. Mitro proposes checking affirmative consent on the legacy import route.
6. **Close with review controls.** Explain that the proposal is a candidate engineering interpretation. Human review is still needed to confirm applicability and accept the change; there is no GitHub push.

## Presenter notes

- No customer records are needed; Lendwise uses synthetic code and fake integration endpoints.
- The DLG calculation is intentionally simplified and stage-level. It demonstrates a software regression test, not an ECL accounting methodology.
- Keep the statement “candidate for review” visible when discussing scan results.
- The local SQLite database retains the sample approval between launches. If you want a clean rehearsal, restore a copy of the original `data/mitro.db` or use a fresh project copy; do not delete the only copy of your demo data.
- If presenting from a public host, do not upload non-public regulatory material, real borrower data, API keys, or company source code. The prototype has no user authentication.
