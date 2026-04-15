"""
File-system tools.

All file operations are sandboxed to the ``output/`` directory
to prevent accidental overwrites elsewhere on the host.
"""

from pathlib import Path
from backend.config import settings


def _safe_path(path_input: str) -> Path:
    """
    Resolve *path_input* to a safe path inside ``output/``.

    Allows nested paths (e.g. ``snippets/utils.py``) but blocks traversal
    and absolute paths outside the sandbox.
    """
    settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    raw = Path(path_input)
    if str(raw).strip() in {"", "."}:
        raise ValueError("Path cannot be empty.")

    sandbox_root = settings.OUTPUT_DIR.resolve()
    candidate = (sandbox_root / raw).resolve()

    if candidate != sandbox_root and sandbox_root not in candidate.parents:
        raise ValueError("Path escapes output sandbox.")
    return candidate


def create_file(filename: str) -> dict:
    """Create a new empty file."""
    try:
        filepath = _safe_path(filename)
    except ValueError as e:
        return {"success": False, "message": str(e)}

    if filepath.exists():
        return {
            "success": False,
            "message": f"File '{filepath.name}' already exists.",
            "path": str(filepath),
        }

    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.touch()
    return {
        "success": True,
        "message": f"Created empty file '{filepath.name}'.",
        "path": str(filepath),
    }


def create_folder(foldername: str) -> dict:
    """Create a new folder inside the output sandbox."""
    try:
        folderpath = _safe_path(foldername)
    except ValueError as e:
        return {"success": False, "message": str(e)}

    if folderpath.exists():
        return {
            "success": False,
            "message": f"Folder '{folderpath.name}' already exists.",
            "path": str(folderpath),
        }

    folderpath.mkdir(parents=True, exist_ok=False)
    return {
        "success": True,
        "message": f"Created folder '{folderpath.name}'.",
        "path": str(folderpath),
    }


def write_code(filename: str, code: str, language: str = "python") -> dict:
    """Write generated code to a file (creates or overwrites)."""
    try:
        filepath = _safe_path(filename)
    except ValueError as e:
        return {"success": False, "message": str(e)}

    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(code, encoding="utf-8")

    return {
        "success": True,
        "message": (
            f"Wrote {language} code to '{filepath.name}' "
            f"({len(code)} chars, {code.count(chr(10)) + 1} lines)."
        ),
        "path": str(filepath),
        "language": language,
        "code": code,
    }
