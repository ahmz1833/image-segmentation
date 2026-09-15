#!/usr/bin/env python3
"""Build and render a self-contained Kaggle training notebook from template.

Packages the current codebase and configs into an in-memory zip archive,
encodes it as base64, and injects it into 'kaggle_train.template.ipynb' to
produce 'kaggle_train.ipynb'.

Usage:
    python scripts/build_kaggle_notebook.py
    # or specify custom template / output:
    python scripts/build_kaggle_notebook.py --template kaggle_train.template.ipynb --output kaggle_train.ipynb
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import os
import sys
import zipfile
from pathlib import Path


def create_code_zip_bytes(repo_dir: Path) -> bytes:
    """Package project sources and configurations into an in-memory zip."""
    zip_buffer = io.BytesIO()

    include_dirs = ["src", "configs", "scripts"]
    include_files = ["kaggle_runner.py", "pyproject.toml", "requirements.txt", "README.md"]

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for dir_name in include_dirs:
            full_dir = repo_dir / dir_name
            if not full_dir.is_dir():
                continue
            for root, _, files in os.walk(full_dir):
                for f in files:
                    if (
                        f.endswith((".pyc", ".pyo", ".git"))
                        or "__pycache__" in root
                        or ".egg-info" in root
                    ):
                        continue
                    file_path = Path(root) / f
                    arcname = file_path.relative_to(repo_dir).as_posix()
                    zf.write(file_path, arcname)

        for file_name in include_files:
            file_path = repo_dir / file_name
            if file_path.is_file():
                zf.write(file_path, file_name)

    return zip_buffer.getvalue()


def build_notebook(
    template_path: Path,
    output_path: Path,
    repo_dir: Path,
    save_zip: Path | None = None,
) -> Path:
    """Render template notebook with embedded base64 code zip."""
    if not template_path.is_file():
        raise FileNotFoundError(f"Template notebook not found: {template_path}")

    print(f"Packaging codebase from: {repo_dir}")
    zip_bytes = create_code_zip_bytes(repo_dir)
    b64_str = base64.b64encode(zip_bytes).decode("ascii")
    print(f"Created codebase archive ({len(zip_bytes):,} bytes, base64: {len(b64_str):,} chars)")

    if save_zip:
        save_zip.write_bytes(zip_bytes)
        print(f"Saved standalone zip archive: {save_zip}")

    template_content = template_path.read_text(encoding="utf-8")
    if "__CODE_ZIP_B64__" not in template_content:
        raise ValueError(
            f"Placeholder '__CODE_ZIP_B64__' not found in template: {template_path}"
        )

    rendered = template_content.replace("__CODE_ZIP_B64__", b64_str)
    # Validate that it's valid JSON
    json.loads(rendered)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")
    print(f"Rendered final self-contained notebook: {output_path} ({output_path.stat().st_size:,} bytes)")
    return output_path


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent

    parser = argparse.ArgumentParser(description="Render self-contained Kaggle notebook from template.")
    parser.add_argument(
        "--template",
        type=Path,
        default=repo_root / "kaggle_train.template.ipynb",
        help="Path to template notebook (default: kaggle_train.template.ipynb)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=repo_root / "kaggle_train.ipynb",
        help="Path to output rendered notebook (default: kaggle_train.ipynb)",
    )
    parser.add_argument(
        "--save-zip",
        type=Path,
        default=repo_root / "kaggle_code.zip",
        help="Optional path to save standalone zip archive (default: kaggle_code.zip)",
    )
    args = parser.parse_args()

    build_notebook(
        template_path=args.template,
        output_path=args.output,
        repo_dir=repo_root,
        save_zip=args.save_zip,
    )


if __name__ == "__main__":
    main()
