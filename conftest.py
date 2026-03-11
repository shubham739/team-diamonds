"""Root conftest.py — adds all source packages to sys.path.

Pytest picks this file up automatically before collecting any tests.
It inserts both package src/ directories onto sys.path so that every
import in the test suite resolves correctly for pytest, Pylint, and Pylance.

Project layout:
    team-diamonds/
    ├── conftest.py                                 ← this file
    ├── components/
    │   ├── jira_client_impl/
    │   │   └── src/
    │   │       └── jira_client_impl/               ← importable package
    │   └── work_mgmt_client_interface/
    │       └── src/
    │           └── work_mgmt_client_interface/     ← importable package
    └── tests/
        └── integration/
            └── test_client_integration.py
"""

import sys
from pathlib import Path

# The directory that contains this conftest.py (team-diamonds/).
PROJECT_ROOT = Path(__file__).parent.resolve()

PACKAGE_DIRS: list[Path] = [
    # jira_client_impl lives at components/jira_client_impl/src/
    PROJECT_ROOT / "components" / "jira_client_impl" / "src",
    # work_mgmt_client_interface lives at components/work_mgmt_client_interface/src/
    PROJECT_ROOT / "components" / "work_mgmt_client_interface" / "src",
]

for pkg_dir in PACKAGE_DIRS:
    pkg_dir_str = str(pkg_dir)
    if pkg_dir_str not in sys.path:
        sys.path.insert(0, pkg_dir_str)