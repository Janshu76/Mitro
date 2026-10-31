"""Rebuild the standalone variant from the unchanged functional baseline."""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
original = (root / "web/index.html").read_text(encoding="utf-8")
page = original.replace('<title>Mitro | Regulatory engineering</title>', '<title>Mitro | From regulation to review</title>')
page = page.replace('</head>', '<link rel="stylesheet" href="optimus.css">\n</head>')
page = page.replace('<meta name="theme-color" content="#12372f">', '<meta name="theme-color" content="#f7f8f4">')
page = re.sub(r'<header>.*?</header>', '<header><div class="brand">mitro<span> / </span></div><p>REGULATORY ENGINEERING<br>LOCAL DEMO WORKSPACE</p></header>', page, count=1, flags=re.S)
overview = '''<section class="view" id="view-start" aria-labelledby="start-title">
  <div class="hero">
    <div class="hero-copy">
      <div class="eyebrow">Evidence before action</div>
      <h1 id="start-title">From regulation<br>to <span>review.</span></h1>
      <p class="hero-description">Understand the clause. Trace its impact. Review the change. A clear path from regulatory wording to engineering work.</p>
      <div class="actions"><button type="button" data-go="documents">Open documents <span aria-hidden="true">&nbsp; ↗</span></button><button type="button" class="secondary" data-go="code">Explore code impact</button></div>
    </div>
    <div class="hero-aside" aria-label="Illustration of Mitro's review process">
      <div class="orb" aria-hidden="true"><div class="orb-inner"><div class="orb-core"></div></div></div>
      <div class="evidence-slip top"><small>01 / REGULATORY EVIDENCE</small><strong>Every clause has a source.</strong><p>Original wording, document versions,<br>and retained source provenance.</p><div class="slip-line">DOCUMENT → CLAUSE → QUOTE</div></div>
      <div class="evidence-slip bottom"><small>02 / ENGINEERING REVIEW</small><strong>A proposal. Then a decision.</strong><p>Inspect candidate code, review the diff,<br>and test a separate edited copy.</p><div class="slip-line">DRAFT → HUMAN REVIEW → EVIDENCE</div></div>
    </div>
  </div>
  <div class="phase-strip"><div><small>PHASE 01 / INTELLIGENCE</small><b>Read the source.</b></div><div><small>PHASE 02 / IMPACT</small><b>Trace the code.</b></div><div><small>PHASE 03 / PROPOSAL</small><b>Review the change.</b></div></div>
  <div class="work-heading"><div><div class="eyebrow">Your workspace</div><h2>Clarity at every step.</h2></div><p>Move from source text to a reviewable engineering proposal. Keep the evidence close.</p></div>
  <div class="task-grid">
    <article class="task"><span class="task-number">01</span><div><h3>A library you can inspect.</h3><p>Upload a regulation, browse included sources, check official URLs, or compare document versions.</p><button type="button" data-go="documents">Open document library <span aria-hidden="true">↗</span></button></div></article>
    <article class="task"><span class="task-number">02</span><div><h3>The wording comes first.</h3><p>Read extracted clauses, filter by reference, and draft obligations grounded in the exact quote.</p><button type="button" data-go="clauses">Review clauses &amp; obligations <span aria-hidden="true">↗</span></button></div></article>
    <article class="task"><span class="task-number">03</span><div><h3>Find the engineering thread.</h3><p>Scan Lendwise or a registered local folder. Inspect readable findings, raw results, and code previews.</p><button type="button" data-go="code">Open code analysis <span aria-hidden="true">↗</span></button></div></article>
    <article class="task"><span class="task-number">04</span><div><h3>Make changes reviewable.</h3><p>For supported clauses, inspect a proposed diff, build a separate edited copy, and review regression evidence.</p><button type="button" data-go="clauses">Start with a clause <span aria-hidden="true">↗</span></button></div></article>
  </div>
  <div class="scope-note"><strong>Built for human review.</strong><p>Mitro surfaces review candidates, not legal conclusions. Source checks run on demand. Code scans are read only; supported patch builds write to a separate Lendwise copy.</p></div>
</section>'''
page = re.sub(r'<section class="view" id="view-start".*?</section>', lambda _: overview, page, count=1, flags=re.S)
page = page.replace('<footer>Mitro local demo · Human review required · No code is changed by this prototype.</footer>', '<footer><span>mitro / Regulatory engineering</span><span>Local demo · Human review required · Original code preserved</span></footer>')
# Preserve intended impact behavior while making its JSON result visible.
page = page.replace('showView("code");byId("scanout").textContent="Finding candidate locations…"', 'showView("code");setScanMode("json");byId("scanout").textContent="Finding candidate locations…"')
# Render API errors as text, including untrusted source-derived messages.
page = page.replace("dest.innerHTML='<div class=\"empty\">'+e.message+'</div>'", 'dest.replaceChildren(node("p",e.message))')
# Copying a candidate quote should expose the target form.
page = page.replace('byId("statement").value="Reviewer: describe the concrete engineering action required by this clause.";byId("statement").focus()', 'byId("statement").value="Reviewer: describe the concrete engineering action required by this clause.";byId("obform").closest("details").open=true;byId("statement").focus()')
(root / "design/mitro-optimus.html").write_text(page, encoding="utf-8")

baseline_ids = set(re.findall(r'\bid="([^"]+)"', original))
variant_ids = re.findall(r'\bid="([^"]+)"', page)
assert baseline_ids <= set(variant_ids), baseline_ids - set(variant_ids)
assert len(variant_ids) == len(set(variant_ids)), "Duplicate IDs"
print(f"Built design/mitro-optimus.html; retained all {len(baseline_ids)} baseline element IDs.")
