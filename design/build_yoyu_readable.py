"""Duplicate the animated Yoyu preview with an independent typography override."""
from pathlib import Path
import hashlib
import re
import subprocess

design = Path(__file__).resolve().parent
source = design / "mitro-yoyu.html"
protected = {p:hashlib.sha256(p.read_bytes()).hexdigest() for p in design.iterdir() if p.is_file() and p.name not in {"mitro-yoyu-readable.html", "yoyu-readable-motion.js", ".readable-motion-check.js", "mitro-yoyu-readable-preview.png"}}
page = source.read_text(encoding="utf-8")
page = page.replace('<title>Mitro | A clearer review</title>', '<title>Mitro | Readable pixel workspace</title>')
page = page.replace('src="yoyu-motion.js"', 'src="yoyu-readable-motion.js"')
page = page.replace('</head>', '<link rel="stylesheet" href="yoyu-readable.css">\n</head>')
page = page.replace('href="mitro-yoyu.html" aria-label="Mitro Yoyu preview"', 'href="mitro-yoyu-readable.html" aria-label="Mitro readable Yoyu preview"')
page = page.replace('PIXEL WORKSPACE<br>LOCAL DEMONSTRATION', 'PIXEL WORKSPACE<br>READABLE EDITION')
page = page.replace('<a href="previews.html">OTHER PREVIEWS ↗</a>', '<a href="mitro-yoyu.html">Original version ↗</a><a href="previews.html">Other previews ↗</a>')
page = page.replace('>REFERENCE ↗</a>', '>Reference ↗</a>')
page = page.replace(': ] MITRO / A CLEARER REVIEW', ': ] MITRO / READABLE EDITION')
(design / 'mitro-yoyu-readable.html').write_text(page, encoding='utf-8')
# Keep motion preferences independent so this duplicate cannot alter the original's setting.
motion = (design / 'yoyu-motion.js').read_text(encoding='utf-8').replace("'mitro-yoyu-motion'", "'mitro-yoyu-readable-motion'")
(design / 'yoyu-readable-motion.js').write_text(motion, encoding='utf-8')
check = design / '.readable-motion-check.js'
try:
    check.write_text(motion,encoding='utf-8')
    subprocess.run(['node','--check',str(check)],check=True)
finally:
    check.unlink(missing_ok=True)
source_ids = re.findall(r'\bid="([^"]+)"',source.read_text(encoding='utf-8'))
assert re.findall(r'\bid="([^"]+)"',page)==source_ids
assert re.search(r'<script>(.*?)</script>',page,re.S).group(1)==re.search(r'<script>(.*?)</script>',source.read_text(encoding='utf-8'),re.S).group(1)
for path,digest in protected.items():
    assert hashlib.sha256(path.read_bytes()).hexdigest()==digest, f'Existing file changed: {path}'
print('Created readable duplicate. All existing preview files and functional handlers unchanged.')
