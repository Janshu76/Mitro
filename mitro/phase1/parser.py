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

def _read_pdf_pages(path: Path) -> list[str]:
    if fitz is not None:
        with fitz.open(path) as doc:
            return [page.get_text("text", sort=True) for page in doc]
    from pypdf import PdfReader
    return [page.extract_text() or "" for page in PdfReader(str(path)).pages]

def _ocrmypdf_searchable_copy(path: Path) -> tuple[list[str] | None, str]:
    """Use OCRmyPDF for low-text PDFs; preserve a searchable copy only as an extraction temp."""
    try:
        import ocrmypdf
    except ImportError:
        return None, "ocrmypdf_unavailable"
    try:
        with tempfile.TemporaryDirectory(prefix="mitro-ocrmypdf-") as tmp:
            output = Path(tmp) / "searchable.pdf"
            ocrmypdf.ocr(str(path), str(output), deskew=True, rotate_pages=True,
                         skip_text=True, jobs=1, progress_bar=False, output_type="pdf")
            return _read_pdf_pages(output), "ocrmypdf"
    except Exception as exc:
        return None, f"ocrmypdf_failed:{type(exc).__name__}"

def _paddle_ocr_pages(path: Path) -> tuple[list[str] | None, list[float], str]:
    """Fallback OCR for hard pages, supporting the PaddleOCR 2.x and 3.x APIs."""
    try:
        from paddleocr import PaddleOCR
    except ImportError:
        return None, [], "paddleocr_unavailable"
    if fitz is None:
        return None, [], "paddleocr_requires_pymupdf_rendering"
    try:
        import statistics
        try:
            engine = PaddleOCR(lang="en", show_log=False)
        except TypeError:
            engine = PaddleOCR(lang="en")
        pages, confidence = [], []
        with tempfile.TemporaryDirectory(prefix="mitro-paddleocr-") as tmp, fitz.open(path) as doc:
            for index, page in enumerate(doc):
                image = Path(tmp) / f"page-{index + 1:04d}.png"
                page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False).save(image)
                if hasattr(engine, "predict"):
                    result = engine.predict(str(image))
                    texts, scores = [], []
                    for item in result or []:
                        payload = item if isinstance(item, dict) else getattr(item, "json", {})
                        if callable(payload):
                            payload = payload()
                        if isinstance(payload, str):
                            import json
                            payload = json.loads(payload)
                        if isinstance(payload, dict):
                            payload = payload.get("res", payload)
                            texts.extend(str(t) for t in payload.get("rec_texts", []))
                            scores.extend(float(s) for s in payload.get("rec_scores", []))
                else:
                    result = engine.ocr(str(image), cls=True)
                    texts, scores = [], []
                    for line in (result or [[]])[0] or []:
                        if len(line) > 1:
                            texts.append(str(line[1][0]))
                            scores.append(float(line[1][1]))
                pages.append("\n".join(texts))
                if scores:
                    confidence.append(statistics.mean(scores))
        return pages, confidence, "paddleocr"
    except Exception as exc:
        return None, [], f"paddleocr_failed:{type(exc).__name__}"

def extract_pdf_pages(path: Path) -> tuple[list[str], str]:
    """Select text/OCR by document content and keep page boundaries for source citations."""
    if path.suffix.lower() != ".pdf":
        text, method = extract_text(path)
        return [text], method
    try:
        pages = _read_pdf_pages(path)
    except Exception as exc:
        raise ValueError(f"Could not read PDF: {exc}") from exc
    method = "pymupdf-text" if fitz is not None else "pypdf-text"
    if sum(len(re.sub(r"\s", "", page)) for page in pages) < 200:
        method = "low-text-needs-ocr"
        candidate, ocr_method = _ocrmypdf_searchable_copy(path)
        if candidate and sum(map(len, candidate)) > sum(map(len, pages)):
            pages, method = candidate, "ocrmypdf-needs-human-verification"
        else:
            candidate, _, paddle_method = _paddle_ocr_pages(path)
            if candidate and sum(map(len, candidate)) > sum(map(len, pages)):
                pages, method = candidate, "paddleocr-needs-human-verification"
            else:
                tesseract = shutil.which("tesseract")
                if tesseract and fitz is not None:
                    try:
                        candidate = []
                        with tempfile.TemporaryDirectory(prefix="mitro-ocr-") as tmp, fitz.open(path) as doc:
                            for i, page in enumerate(doc):
                                image = Path(tmp) / f"page-{i + 1:04d}.png"
                                page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False).save(image)
                                result = subprocess.run([tesseract, str(image), "stdout", "-l", "eng"],
                                    check=True, capture_output=True, text=True, timeout=45)
                                candidate.append(result.stdout)
                        if sum(map(len, candidate)) > sum(map(len, pages)):
                            pages, method = candidate, "tesseract-ocr-needs-human-verification"
                    except (OSError, subprocess.SubprocessError):
                        pass
            if method == "low-text-needs-ocr":
                method += f" ({ocr_method}; {paddle_method})"
    return pages, method

def extract_pdf_document(path: Path) -> tuple[list[str], str, dict]:
    """Extract page text plus Docling's structured artifact when available."""
    pages, method = extract_pdf_pages(path)
    confidence = 0.88 if method.startswith("pymupdf") else 0.82 if method.startswith("pypdf") else 0.62
    if "needs-human-verification" in method:
        confidence = 0.62 if "ocrmypdf" in method else 0.58 if "paddleocr" in method else 0.55
    elif "low-text-needs-ocr" in method:
        confidence = 0.25
    details: dict = {"page_count": len(pages), "parser_versions": {}, "page_coordinates": [],
                     "page_confidence": [round(confidence if page.strip() else 0.1, 2) for page in pages],
                     "confidence_note": "Heuristic extraction confidence; reviewers must verify against the original PDF."}
    if path.suffix.lower() != ".pdf":
        return pages, method, details
    if fitz is not None:
        try:
            with fitz.open(path) as pdf:
                for page_number, page in enumerate(pdf, 1):
                    blocks = []
                    for block in page.get_text("blocks"):
                        if len(block) >= 5 and str(block[4]).strip():
                            blocks.append({"bbox": [round(float(v), 2) for v in block[:4]],
                                           "text": str(block[4]).strip()[:1200]})
                    details["page_coordinates"].append({"page": page_number,
                        "width": round(page.rect.width, 2), "height": round(page.rect.height, 2),
                        "text_blocks": blocks})
        except Exception:
            details["coordinate_warning"] = "Page coordinates could not be extracted."
    try:
        import importlib.metadata as package_metadata
        for package in ("pymupdf", "pypdf", "ocrmypdf", "paddleocr", "docling"):
            try:
                details["parser_versions"][package] = package_metadata.version(package)
            except package_metadata.PackageNotFoundError:
                continue
    except Exception:
        pass
    try:
        import docling
        from docling.document_converter import DocumentConverter
        converted = DocumentConverter().convert(str(path))
        document = converted.document
        details["structured_markdown"] = document.export_to_markdown()
        details["structured_document"] = document.export_to_dict()
        details["parser_versions"]["docling"] = getattr(docling, "__version__", "unknown")
        method = "docling+" + method
    except ImportError:
        details["structured_warning"] = "Docling is not installed; page text extraction fallback was used."
    except Exception as exc:
        details["structured_warning"] = f"Docling extraction failed ({type(exc).__name__}); page text fallback was used."
    return pages, method, details

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

def split_page_clauses(pages: list[str]) -> list[tuple[str, str, int]]:
    """Segment across page boundaries while retaining the page where each chunk starts."""
    chunks: list[tuple[str, str, int]] = []
    current_id, current, current_page = "", [], 1
    generated = 0
    def flush():
        nonlocal current, current_id, generated
        body = " ".join(x.strip() for x in current if x.strip()).strip()
        if body:
            if not current_id:
                generated += 1
                current_id = f"paragraph-{generated:04d}"
            chunks.append((current_id, body, current_page))
        current, current_id = [], ""
    for page_number, page_text in enumerate(pages, 1):
        for raw in page_text.splitlines():
            line = re.sub(r"\s+", " ", raw).strip()
            if not line:
                continue
            match = _CLAUSE.match(line)
            if match:
                flush()
                current_id, current_page = match.group(1).rstrip("."), page_number
                current.append(match.group(2))
            elif current:
                current.append(line)
            elif len(line) > 40:
                current_page = page_number
                current.append(line)
    flush()
    return chunks

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

