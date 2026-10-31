"""Create the Yoyu-inspired preview without changing existing designs."""
from pathlib import Path
import hashlib
import re
import subprocess

root = Path(__file__).resolve().parents[1]
design = root / "design"
protected = [root / "web/index.html", root / "mitro/api/app.py"] + [p for p in design.iterdir() if p.is_file() and p.name not in {"mitro-yoyu.html", "mitro-yoyu-preview.png", ".yoyu-check.js"}]
before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
original = (root / "web/index.html").read_text(encoding="utf-8")
script = re.search(r'<script>(.*?)</script>', (design / "mitro-optimus.html").read_text(encoding="utf-8"), re.S).group(1)

def pixel_svg(kind):
    common = 'viewBox="0 0 160 160" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"'
    if kind == "document":
        body = '<path fill="#252525" d="M42 12h62v12h14v12h14v108H28V12z"/><path fill="#fff" d="M40 24h54v24h26v84H40z"/><path fill="#16876f" d="M96 24h10v12h14v10H96z"/><path fill="#252525" d="M52 59h12v12H52zm36 0h12v12H88zM52 88h12v12h24V88h12v24H52z"/><path class="pixel-speck" d="M6 38h6v6h6v6h-6v6H6v-6H0v-6h6zm134 64h6v6h6v6h-6v6h-6v-6h-6v-6h6z"/>'
    elif kind == "review":
        body = '<path fill="#252525" d="M46 16h68v12h14v14h14v70h-14v14h-14v14H46v-14H32v-14H18V42h14V28h14z"/><path fill="#fff" d="M48 30h64v14h16v66h-16v16H48v-16H32V44h16z"/><path fill="#252525" d="M50 58h12v12H50zm46 0h12v12H96zM52 88h12v12h32V88h12v24H52z"/><path fill="#16876f" d="M108 4h8v8h8v8h-8v8h-8v-8h-8v-8h8zM2 88h6v6h6v6H8v6H2v-6h-6v-6h6z"/>'
    else:
        body = '<path fill="#252525" d="M16 30h128v94H92v12h24v12H44v-12h24v-12H16z"/><path fill="#fff" d="M28 42h104v70H28z"/><path fill="#252525" d="M52 58H40v12H28v12h12v12h12V82H40V70h12zm56 0h12v12h12v12h-12v12h-12V82h12V70h-12z"/><path fill="#16876f" d="M80 54h12L80 100H68zM4 4h6v6h6v6h-6v6H4v-6h-6v-6h6zm142 136h6v6h6v6h-6v6h-6v-6h-6v-6h6z"/>'
    return f'<svg {common}>{body}</svg>'

hero = f'''<section class="view" id="view-start" aria-labelledby="start-title"><div class="yoyu-hero"><p class="kicker">REGULATORY ENGINEERING / A LITTLE MORE CLARITY</p><h1 class="yoyu-title" id="start-title"><span class="pixel-bracket" aria-hidden="true">: ]</span>mitro<span class="pixel-bracket" aria-hidden="true">[ :</span></h1><p class="hero-description">Make room for a clearer review.<br>From regulatory wording to the code that may need attention.</p><div class="pixel-stage"><figure class="pixel-figure">{pixel_svg("document")}<figcaption>01 / SOURCE<br><span>Read the wording.</span></figcaption></figure><figure class="pixel-figure center">{pixel_svg("review")}<figcaption>02 / REVIEW<br><span>Keep people in the loop.</span></figcaption></figure><figure class="pixel-figure">{pixel_svg("code")}<figcaption>03 / CODE<br><span>Explore the impact.</span></figcaption></figure></div><div class="hero-actions"><button type="button" data-go="documents">Start with a document <span aria-hidden="true">▤ ↗</span></button><button type="button" class="secondary" data-go="code">Explore code impact <span aria-hidden="true">↗</span></button></div></div><div class="path-guide"><div><small>STEP 01</small>Read a source.</div><div><small>STEP 02</small>Review a clause.</div><div><small>STEP 03</small>Trace the code.</div></div><div class="work-section"><p class="kicker">PICK YOUR NEXT STEP</p><h2>A place for every<br>part of the review.</h2><div class="work-list">'''
tasks = [
    ("01", "Your source library", "Upload public regulations, browse included documents, check official URLs, and compare versions.", "documents", "Open documents"),
    ("02", "Words, in context", "Inspect clauses and exact quotes. Draft obligations for an explicit human decision.", "clauses", "Review clauses"),
    ("03", "Follow the code", "Scan Lendwise or a registered local folder. Explore readable findings, JSON, and code previews.", "code", "Open code analysis"),
    ("04", "A change to consider", "For supported clauses, inspect a proposed diff, build a separate edited copy, and review its test evidence.", "clauses", "Start from a clause"),
]
for number,title,desc,view,label in tasks:
    hero += f'<article class="work-item"><span class="num">{number}</span><div><h3>{title}</h3><p>{desc}</p><button type="button" data-go="{view}">{label} <span aria-hidden="true">↗</span></button></div></article>'
hero += '</div></div><aside class="boundary"><b>Small steps.<br>Human decisions.</b><p>Mitro finds candidates for review, not legal conclusions. Source checks run on demand. Code scans are read only; supported patch builds write to a separate Lendwise copy.</p></aside></section>'
page = original.replace('<title>Mitro | Regulatory engineering</title>', '<title>Mitro | A clearer review</title>')
page = page.replace('<meta name="theme-color" content="#12372f">','<meta name="theme-color" content="#ffffff">')
page = page.replace('</head>','<link rel="stylesheet" href="preview-core.css"><link rel="stylesheet" href="yoyu.css"><link rel="stylesheet" href="yoyu-motion.css"><script src="yoyu-motion.js" defer></script>\n</head>')
header = '<header><a class="brand" href="mitro-yoyu.html" aria-label="Mitro Yoyu preview">: ] mitro<span>.</span></a><p>PIXEL WORKSPACE<br>LOCAL DEMONSTRATION</p><div class="preview-links"><a href="previews.html">OTHER PREVIEWS ↗</a><a href="https://yoyu.design/" target="_blank" rel="noopener noreferrer">REFERENCE ↗</a></div></header>'
page = re.sub(r'<header>.*?</header>',lambda _:header,page,count=1,flags=re.S)
page = re.sub(r'<section class="view" id="view-start".*?</section>',lambda _:hero,page,count=1,flags=re.S)
page = re.sub(r'<script>.*?</script>',lambda _:'<script>'+script+'</script>',page,count=1,flags=re.S)
page = page.replace('<footer>Mitro local demo · Human review required · No code is changed by this prototype.</footer>','<footer><span>: ] MITRO / A CLEARER REVIEW</span><span>Local demo · Human review required · Original code preserved</span></footer>')
ids = re.findall(r'\bid="([^"]+)"',page)
assert set(re.findall(r'\bid="([^"]+)"',original)) <= set(ids)
assert len(ids)==len(set(ids))
(design/'mitro-yoyu.html').write_text(page,encoding='utf-8')
check = design/'.yoyu-check.js'
try:
    check.write_text(script,encoding='utf-8')
    subprocess.run(['node','--check',str(check)],check=True)
finally:
    check.unlink(missing_ok=True)
for p,digest in before.items():
    assert hashlib.sha256(p.read_bytes()).hexdigest()==digest, f'Existing file changed: {p}'
print(f'Built Yoyu preview. All {len(ids)} original IDs retained. Existing designs and backend unchanged.')
