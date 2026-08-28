from __future__ import annotations

from pathlib import Path


def load_document(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        try:
            import fitz
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("PDF support requires PyMuPDF") from exc
        with fitz.open(path) as doc:
            text = "\n\n".join(page.get_text("text") for page in doc)
    elif suffix in {".txt", ".md"}:
        text = path.read_text(encoding="utf-8")
    else:
        raise ValueError(f"Unsupported document type {suffix}; use PDF, TXT, or MD")
    normalized = text.replace("\x00", "").strip()
    if not normalized:
        raise ValueError(f"No text could be extracted from {path}")
    return normalized
