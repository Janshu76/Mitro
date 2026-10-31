"""One-time promotion that preserves the latest workbench functionality."""
from pathlib import Path
import hashlib
import re
import subprocess

root = Path(__file__).resolve().parents[1]
design = root / 'design'
web = root / 'web'
current = (web/'index.html').read_text(encoding='utf-8')
if '/static/mitro-ui/' in current:
    raise SystemExit('Readable UI is already promoted; do not overwrite subsequent changes.')
selected = (design/'mitro-yoyu-readable.html').read_text(encoding='utf-8')
protected = {p:hashlib.sha256(p.read_bytes()).hexdigest() for p in design.iterdir() if p.is_file()}

# A reversible snapshot of the latest working page, including its added features.
archive = design/'archive'
archive.mkdir(exist_ok=True)
backup = archive/'main-before-readable.html'
if backup.exists():
    raise SystemExit('Promotion backup already exists; inspect before retrying.')
backup.write_bytes((web/'index.html').read_bytes())

# Keep current forms/handlers: the approved preview predates dependency/audit features.
updates = re.search(r'<section class="view" id="view-updates".*?</section>',current,re.S).group(0)
page = selected.replace('<footer>',updates+'\n<footer>',1)
nav = '<button type="button" data-view="updates" aria-pressed="false">Change &amp; dependency impact</button>'
page = page.replace('</nav>',nav+'\n</nav>',1)
script = re.search(r'<script>(.*?)</script>',current,re.S).group(1)
# Carry forward the preview's small behavior fixes without dropping recent features.
script = script.replace('showView("code");byId("scanout").textContent="Finding candidate locations…"', 'showView("code");setScanMode("json");byId("scanout").textContent="Finding candidate locations…"')
script = script.replace("dest.innerHTML='<div class=\"empty\">'+e.message+'</div>'",'dest.replaceChildren(node("p",e.message))')
script = script.replace('byId("statement").value="Reviewer: describe the concrete engineering action required by this clause.";byId("statement").focus()', 'byId("statement").value="Reviewer: describe the concrete engineering action required by this clause.";byId("obform").closest("details").open=true;byId("statement").focus()')
page = re.sub(r'<script>.*?</script>',lambda _:'<script>'+script+'</script>',page,count=1,flags=re.S)
page = page.replace('<title>Mitro | Readable pixel workspace</title>','<title>Mitro | Regulatory engineering</title>')
page = page.replace('href="mitro-yoyu-readable.html" aria-label="Mitro readable Yoyu preview"','href="/" aria-label="Mitro home"')
page = page.replace('PIXEL WORKSPACE<br>READABLE EDITION','REGULATORY ENGINEERING<br>LOCAL DEMO WORKSPACE')
page = re.sub(r'<div class="preview-links">.*?</div>', '<div class="preview-links"><a href="/workbench">Workbench</a><a href="/static/theme-options.html">Design options ↗</a></div>',page,count=1,flags=re.S)
page = page.replace(': ] MITRO / READABLE EDITION',': ] MITRO / REGULATORY ENGINEERING')
page = page.replace('<span>Local demo · Human review required · Original code preserved</span>','<span>Local demo · Human review required · Original code preserved</span>')

assets = web/'mitro-ui'
assets.mkdir(exist_ok=True)
for name in ['preview-core.css','yoyu.css','yoyu-motion.css','yoyu-readable.css']:
    (assets/name).write_bytes((design/name).read_bytes())
    page = page.replace(f'href="{name}"',f'href="/static/mitro-ui/{name}"')
motion = (design/'yoyu-readable-motion.js').read_text(encoding='utf-8').replace("'mitro-yoyu-readable-motion'","'mitro-ui-motion'")
(assets/'motion.js').write_text(motion,encoding='utf-8')
page = page.replace('src="yoyu-readable-motion.js"','src="/static/mitro-ui/motion.js"')
# A compact last tab on narrow screens; keep every existing destination available.
page = page.replace('</head>','<link rel="stylesheet" href="/static/mitro-ui/main.css">\n</head>')
(assets/'main.css').write_text('.nav{flex-wrap:wrap}.nav button{padding-left:14px;padding-right:14px;font-size:14px}@media(max-width:767px){.nav button[data-view="updates"]{grid-column:1/-1}.nav button{font-size:14px}}\n',encoding='utf-8')

old_ids = set(re.findall(r'\bid="([^"]+)"',current))
new_ids = re.findall(r'\bid="([^"]+)"',page)
assert old_ids <= set(new_ids), old_ids-set(new_ids)
assert len(new_ids)==len(set(new_ids)), 'Duplicate IDs'
check = design/'.main-ui-check.js'
try:
    check.write_text(script,encoding='utf-8')
    subprocess.run(['node','--check',str(check)],check=True)
    subprocess.run(['node','--check',str(assets/'motion.js')],check=True)
finally:
    check.unlink(missing_ok=True)
(web/'index.html').write_text(page,encoding='utf-8')
for p,digest in protected.items():
    assert hashlib.sha256(p.read_bytes()).hexdigest()==digest, f'Preview changed: {p}'
print(f'Promoted selected design; all {len(old_ids)} current workbench IDs retained, every preview unchanged.')
