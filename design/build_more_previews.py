"""Create additional previews without writing to any existing design variant."""
from pathlib import Path
import hashlib
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / "design"
protected = [ROOT / p for p in (
    "web/index.html", "design/mitro-optimus.html", "design/optimus.css",
    "design/ui-overview.html", "design/build_variant.py", "mitro/api/app.py")]
before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
original = (ROOT / "web/index.html").read_text(encoding="utf-8")
# Reuse the functional script already checked in the first preview; keep that file intact.
script = re.search(r"<script>(.*?)</script>", (DESIGN / "mitro-optimus.html").read_text(encoding="utf-8"), re.S).group(1)

TASKS = [
    ("01", "Document evidence", "Browse the library, add a public source, check official URLs, and compare versions of the same regulation.", "documents", "Open library"),
    ("02", "Clauses & obligations", "Inspect exact wording, draft an engineering requirement, and record an explicit human review.", "clauses", "Review clauses"),
    ("03", "Code impact", "Scan the synthetic Lendwise app or a registered local folder. Inspect candidate findings and code previews.", "code", "Explore code"),
    ("04", "Reviewable changes", "Start from a supported clause, inspect a diff, then build and test a separate edited Lendwise copy.", "clauses", "Start a proposal"),
]

def tasks(heading, kicker):
    rows = "".join(f'<article class="work-item"><span class="num">{n}</span><div><h3>{title}</h3><p>{desc}</p><button type="button" data-go="{view}">{label} <span aria-hidden="true">&nbsp;↗</span></button></div></article>' for n,title,desc,view,label in TASKS)
    return f'<div class="work-section"><p class="kicker">{kicker}</p><h2>{heading}</h2><div class="work-list">{rows}</div></div><aside class="boundary"><b>Evidence stays in view.</b><p>Matches are candidates for human review, not legal conclusions. Source checks run on demand. Scans are read only. Supported patch builds write to a separate Lendwise copy.</p></aside>'

CHRISTEN = '''
<div class="terminal-meta"><div>WORKSPACE<br><b>MITRO / LOCAL DEMO</b></div><div>REGULATORY ENGINEERING<br><b>DOCUMENTS · CLAUSES · CODE</b></div><div>REVIEW PROTOCOL<br><b>HUMAN DECISION REQUIRED</b></div></div>
<div class="christen-hero"><div><p class="kicker">[ 00 ] / Evidence-led engineering</p><h1 class="display" id="start-title">Reading the rule.<br><span>Tracing the<br>impact.</span></h1><p class="hero-description">Connect regulatory wording to possible engineering work. Keep the source, the reasoning, and the review together.</p><div class="hero-actions"><button type="button" data-go="documents">OPEN DOCUMENTS ↗</button><button type="button" class="secondary" data-go="code">INSPECT CODE</button></div></div><div class="christen-art"><div class="dither-object" aria-hidden="true"></div><div class="spec-box"><div><span>INPUT</span><b>REGULATORY SOURCE</b></div><div><span>PROCESS</span><b>EXTRACT / REVIEW / MAP</b></div><div><span>OUTPUT</span><b>ENGINEERING CANDIDATE</b></div><div><span>AUTHORITY</span><b>HUMAN REVIEWER</b></div></div></div></div><div class="mega-word" aria-hidden="true">MITRO</div>
'''
MECHA = '''
<div class="mecha-hero"><div class="mecha-sigil"><div class="wire-mark" aria-hidden="true"><svg viewBox="0 0 240 280" fill="none" stroke="currentColor" stroke-width="1"><path d="M30 225V65L62 46l58 43 58-43 32 19v160l-32 19V93l-58 43-58-43v151z"/><path d="M30 65l32 28M62 46v47M120 89v47M178 46v47M210 65l-32 28M30 225l32 19M178 225l32 0M46 235V77l16-10 58 43 58-43 16 10v157M62 67v26M120 110v26"/></svg></div><div class="small-index"><div>WORKSPACE / INDEX</div><div>01 &nbsp; REGULATORY EVIDENCE</div><div>02 &nbsp; ENGINEERING IMPACT</div><div>03 &nbsp; REVIEWABLE CHANGE</div></div></div><div class="mecha-main"><div><p class="kicker">⊞ &nbsp; The review workspace</p><h1 class="display" id="start-title">Regulation describes the obligation. Engineering shapes the response. Mitro brings the evidence into focus.</h1></div><div class="mecha-main-bottom"><p class="hero-description">A local workspace for reading regulatory sources, exploring candidate code impact, and reviewing supported change proposals.</p><div class="hero-actions"><button type="button" data-go="documents">Enter the workspace <span aria-hidden="true">↗</span></button></div></div></div></div><div class="editorial-band"><span>SOURCE PROVENANCE</span><span>—</span><span>HUMAN JUDGMENT</span><span>LOCAL DEMO / LENDWISE</span></div>
'''
LAYERS = '''
<div class="cue-strip"><div>01 / INPUT<b>Regulatory sources</b></div><div>02 / ANALYSIS<b>Candidate code impact</b></div><div>03 / OUTPUT<b>Reviewable proposals</b></div><div>WORKSPACE MODE<b>Local demonstration</b></div></div><div class="layers-hero"><div><p class="kicker">A workspace for evidence & engineering</p><h1 class="display" id="start-title">Every change<br>starts with<br>the source.</h1><p class="hero-description">Read the clause. Follow the code. Review a proposal with its evidence in sync.</p><div class="hero-actions"><button type="button" data-go="documents">SOURCE LIBRARY ↗</button><button type="button" class="secondary" data-go="code">CODE ANALYSIS</button></div></div><div class="rig" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i><i></i><i></i></div></div><div class="timeline"><div><small>CUE 01</small><b>Read & retain.</b></div><div><small>CUE 02</small><b>Trace & explain.</b></div><div><small>CUE 03</small><b>Review & test.</b></div></div>
'''
HOOD = '''
<div class="hood-hero"><div class="hood-front"><p class="kicker">01 / The source side</p><h1 class="display" id="start-title">Every rule<br>has an<br><span>engineering<br>side.</span></h1><div class="mini-window" aria-label="Illustration of a regulatory source"><div class="window-top" aria-hidden="true"><i></i><i></i><i></i></div><div class="paper-body"><div class="paper-kicker">REGULATORY EVIDENCE / INPUT</div><strong>Start with<br>the exact wording.</strong><p>Document → version → clause → quote</p><div class="paper-lines" aria-hidden="true"><i></i><i></i><i></i></div></div></div><p class="hero-description">Keep the original source close. Read clauses, draft obligations, and record a human review.</p><div class="hero-actions"><button type="button" data-go="documents">Explore the source ↗</button></div></div><div class="hood-back"><p class="kicker">02 / The code side</p><h2 class="display">Find the<br>connection.<br><span>Review the<br>change.</span></h2><div class="mini-window" aria-label="Illustrative review sequence, not a live execution"><div class="window-top" aria-hidden="true"><i></i><i></i><i></i></div><div class="code-body"><span class="code-comment">// MITRO / REVIEW SEQUENCE</span><br><br>source.read()<br>clause.inspect()<br>impact.explore()<br><span class="code-highlight">reviewer.decide()</span><br><br><span class="code-comment">// A candidate is a starting point.</span></div></div><p class="hero-description">Inspect candidate locations and supported patch proposals. Test a separate copy, keeping original code intact.</p><div class="hero-actions"><button type="button" data-go="code">Look under the hood ↗</button></div></div></div><div class="bridge"><span>REGULATORY WORDING</span><b>↔ MITRO ↔</b><span>ENGINEERING REVIEW</span></div>
'''

variants = [
    ("christen", "Technical dossier", "CHRISTEN DIJOUX", "https://christendijoux.com/", CHRISTEN, "The working parts.", "[ 01—04 ] / Workspace index", "#11130f"),
    ("mecha", "Editorial engineering", "MECHA", "https://mecha-xyz.webflow.io/", MECHA, "From the source,<br>to the system.", "Selected workflows", "#fdfdfb"),
    ("layers", "Evidence control room", "LAYERS OF TIME", "https://layersoftime.studio/", LAYERS, "One source.<br>A clear review sequence.", "CUE 01—04 / Workspace", "#101416"),
    ("hood", "Both sides of the rule", "DEV IN THE HOOD", "https://devinthehood.com/", HOOD, "Choose your next move.", "The workspace / Four ways in", "#f1eee6"),
]

baseline_ids = set(re.findall(r'\bid="([^"]+)"', original))
for slug, title, refname, refurl, hero, heading, kicker, color in variants:
    page = original.replace('<title>Mitro | Regulatory engineering</title>', f'<title>Mitro | {title}</title>')
    page = page.replace('<meta name="theme-color" content="#12372f">', f'<meta name="theme-color" content="{color}">')
    page = page.replace('</head>', f'<link rel="stylesheet" href="preview-core.css"><link rel="stylesheet" href="{slug}.css">\n</head>')
    header = f'<header><a class="brand" href="previews.html" aria-label="Mitro preview gallery">mitro<span> / </span></a><p>{title}<br>LOCAL DEMO WORKSPACE</p><div class="preview-links"><a href="previews.html">ALL PREVIEWS ↗</a><a href="{refurl}" target="_blank" rel="noopener noreferrer">REFERENCE ↗</a></div></header>'
    page = re.sub(r'<header>.*?</header>', lambda _: header, page, count=1, flags=re.S)
    overview = '<section class="view" id="view-start" aria-labelledby="start-title">' + hero + tasks(heading, kicker) + '</section>'
    page = re.sub(r'<section class="view" id="view-start".*?</section>', lambda _: overview, page, count=1, flags=re.S)
    page = re.sub(r'<script>.*?</script>', lambda _: '<script>' + script + '</script>', page, count=1, flags=re.S)
    page = page.replace('<footer>Mitro local demo · Human review required · No code is changed by this prototype.</footer>', f'<footer><span>MITRO / {title.upper()}</span><span>Local demo · Human review required · Original code preserved</span></footer>')
    ids = re.findall(r'\bid="([^"]+)"', page)
    assert baseline_ids <= set(ids), (slug, baseline_ids - set(ids))
    assert len(ids) == len(set(ids)), f"Duplicate ID in {slug}"
    (DESIGN / f'mitro-{slug}.html').write_text(page, encoding='utf-8')
    print(f'{slug}: all {len(baseline_ids)} baseline IDs and existing functional script retained')

check_script = DESIGN / '.additional-preview-check.js'
try:
    check_script.write_text(script, encoding='utf-8')
    subprocess.run(['node', '--check', str(check_script)], check=True)
finally:
    check_script.unlink(missing_ok=True)

cards = []
descriptions = {
    'christen': 'A monochrome technical dossier. Dithered geometry, terminal labels, and a bold typographic signature.',
    'mecha': 'An airy editorial workspace. Asymmetric composition, a wireframe mark, serif display type, and burgundy actions.',
    'layers': 'A dark evidence control room. Cue labels, luminous structural forms, and a measured review sequence.',
    'hood': 'Two sides of one workflow. Warm source documents meet a dark code workspace, connected through review.',
}
for number, (slug,title,refname,refurl,*_) in enumerate(variants, start=2):
    cards.append(f'<a class="gallery-card {slug}" href="mitro-{slug}.html"><div class="card-image"><img src="mitro-{slug}-preview.png" alt="Mitro {title} preview" loading="lazy"></div><div class="card-copy"><span class="tag">0{number} / INSPIRED BY {refname}</span><h2>{title} <span>↗</span></h2><p>{descriptions[slug]}</p><span class="open-label">Open working preview</span></div></a>')
gallery = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Mitro | Design previews</title><link rel="stylesheet" href="gallery.css"></head><body><header><a href="previews.html" class="brand">mitro /</a><span>DESIGN EXPLORATIONS · LOCAL WORKSPACE</span><a href="/">Original UI ↗</a></header><main><div class="gallery-intro"><p class="tag">FOUR NEW DIRECTIONS / ONE WORKING PRODUCT</p><h1>Different perspectives.<br>The same Mitro.</h1><p>Compare four additional designs. Each keeps the document library, clause review, obligations, code scan, and supported proposal workflow connected to the existing local API.</p><div class="preserved"><span>Existing versions, preserved</span><a href="/">Original UI ↗</a><a href="ui-overview.html">Earlier concept ↗</a><a href="mitro-optimus.html">Optimus preview ↗</a></div></div><div class="gallery-grid">''' + ''.join(cards) + '''</div><aside><b>About these previews</b><p>These are separate HTML variants. They use the same local demo data; upload, drafting, approval, and scan actions perform their normal operations. Original pages and backend source have not been replaced. Visuals are inspired by the references rather than copied assets.</p></aside></main><footer>MITRO / DESIGN EXPLORATIONS <span>Human review remains part of every direction.</span></footer></body></html>'''
(DESIGN / 'previews.html').write_text(gallery, encoding='utf-8')

for p, digest in before.items():
    assert hashlib.sha256(p.read_bytes()).hexdigest() == digest, f'Protected file changed: {p}'
print('Verified: all six protected original/design/backend files unchanged.')
