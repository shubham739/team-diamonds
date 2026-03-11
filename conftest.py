"""Root conftest.py — adds all source packages to sys.path."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.resolve()

PACKAGE_DIRS: list[Path] = [
    PROJECT_ROOT / "components" / "jira_client_impl" / "src",
    PROJECT_ROOT / "components" / "work_mgmt_client_interface" / "src",
]

for pkg_dir in PACKAGE_DIRS:
    pkg_dir_str = str(pkg_dir)
    if pkg_dir_str not in sys.path:
        sys.path.insert(0, pkg_dir_str)
