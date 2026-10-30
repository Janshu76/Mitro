from __future__ import annotations
import hashlib, re, shutil, subprocess, tempfile
from pathlib import Path
try:
    import fitz
except (ImportError, OSError):
    # PyMuPDF needs a native DLL that may be blocked by Windows application
    # control. Keep PDF ingestion usable with the pure-Python pypdf fallback.
    fitz = None

_CLAUSE = re.compile(r"^\s*((?:\d+(?:\.\d+){0,4}[A-Z]?(?:\([A-Za-z0-9ivxIVX.-]+\))*)|(?:\([0-9]+\))|(?:[A-Z](?:\.\d+){1,3}))\s*[.)]?\s+(\S.*)$")

def extract_text(path: Path) -> tuple[str, str]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        if fitz is not None:
            doc = fitz.open(path)
            text = "\n\n".join(page.get_text("text", sort=True) for page in doc)
            method = "pymupdf-text"
        else:
            from pypdf import PdfReader
            reader = PdfReader(str(path))
            text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
            method = "pypdf-text"
        if len(re.sub(r"\s", "", text)) < 200:
            method = "low-text-needs-ocr"
            # Use a locally installed Tesseract binary when present. OCR output is
            # explicitly labelled; it is never treated as verified legal text.
            tesseract = shutil.which("tesseract")
            if tesseract and fitz is not None:
                try:
                    pages = []
                    with tempfile.TemporaryDirectory(prefix="mitro-ocr-") as tmp:
                        pdf = fitz.open(path)
                        for i, page in enumerate(pdf):
                            image = Path(tmp) / f"page-{i + 1:04d}.png"
                            page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False).save(image)
                            result = subprocess.run([tesseract, str(image), "stdout", "-l", "eng"],
                                check=True, capture_output=True, text=True, timeout=45)
                            pages.append(result.stdout)
                    ocr_text = "\n\n".join(pages)
                    if len(re.sub(r"\s", "", ocr_text)) > len(re.sub(r"\s", "", text)):
                        text, method = ocr_text, "tesseract-ocr-needs-human-verification"
                except (OSError, subprocess.SubprocessError):
                    pass
        return text, method
    if suffix in {".txt", ".md", ".xml", ".html"}:
        return path.read_text(encoding="utf-8-sig", errors="replace"), "utf-8-text"
    raise ValueError(f"Unsupported document type: {suffix}")

def split_clauses(text: str) -> list[tuple[str, str]]:
    """Conservative clause splitter preserving extracted text."""
    chunks: list[tuple[str, str]] = []
    current_id = ""
    current: list[str] = []
    generated = 0
    def flush():
        nonlocal current, current_id, generated
        body = " ".join(x.strip() for x in current if x.strip()).strip()
        if body:
            if not current_id:
                generated += 1
                current_id = f"paragraph-{generated:04d}"
            chunks.append((current_id, body))
        current, current_id = [], ""
    for raw in text.splitlines():
        line = re.sub(r"\s+", " ", raw).strip()
        if not line: continue
        match = _CLAUSE.match(line)
        if match:
            flush()
            current_id = match.group(1).rstrip(".")
            current.append(match.group(2))
        elif current:
            current.append(line)
        elif len(line) > 40:
            current.append(line)
    flush()
    return chunks

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

