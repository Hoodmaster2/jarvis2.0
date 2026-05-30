"""
PDF Reader skill for JARVIS.
Extracts text and metadata from PDF files.
"""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


async def execute(command: str, **kwargs) -> dict:
    commands = {
        "read": cmd_read,
        "info": cmd_info,
    }
    handler = commands.get(command)
    if not handler:
        return {"error": f"Unknown command: {command}"}
    try:
        return await handler(**kwargs)
    except Exception as e:
        return {"error": str(e)}


async def cmd_read(path: str) -> dict:
    """Extract text from PDF."""
    p = Path(path).resolve()
    if not p.exists() or not p.is_file():
        return {"error": f"File not found: {path}"}

    try:
        import PyPDF2
        with open(p, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            text = []
            for page in reader.pages:
                text.append(page.extract_text())
            return {"content": "\n".join(text), "pages": len(reader.pages)}
    except ImportError:
        pass

    try:
        import pdfminer.high_level as miner
        text = miner.extract_text(str(p))
        return {"content": text, "pages": text.count("\f") + 1}
    except ImportError:
        pass

    try:
        import pdfplumber
        with pdfplumber.open(p) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
            return {"content": text, "pages": len(pdf.pages)}
    except ImportError:
        return {"error": "No PDF library found. Install: pip install PyPDF2"}

    return {"error": "Failed to read PDF"}


async def cmd_info(path: str) -> dict:
    """Get PDF metadata."""
    p = Path(path).resolve()
    if not p.exists():
        return {"error": f"File not found: {path}"}

    try:
        import PyPDF2
        with open(p, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            info = reader.metadata
            return {
                "path": str(p),
                "pages": len(reader.pages),
                "metadata": dict(info) if info else {},
                "size": p.stat().st_size,
            }
    except ImportError:
        return {"error": "PyPDF2 not installed"}
    except Exception as e:
        return {"error": str(e)}
