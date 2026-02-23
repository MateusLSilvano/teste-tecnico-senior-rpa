# app/tests/conftest.py
from __future__ import annotations

import sys
from pathlib import Path


def _ensure_app_package_on_syspath() -> None:
    """
    Repo layout:
      repo_root/
        app/          <- outer folder
          app/        <- python package (import app)
          tests/
    We must add repo_root/app (outer) to sys.path so `import app` works.
    """
    outer_app_dir = Path(__file__).resolve().parents[2]  # .../repo_root/app
    outer_app_dir_str = str(outer_app_dir)
    if outer_app_dir_str not in sys.path:
        sys.path.insert(0, outer_app_dir_str)


_ensure_app_package_on_syspath()