from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def _alembic_cmd() -> list[str]:
    """Resolve alembic for local .venv and CI (pip install, no .venv path)."""
    local = Path(__file__).resolve().parents[2] / ".venv" / "bin" / "alembic"
    if local.is_file():
        return [str(local)]
    found = shutil.which("alembic")
    if found:
        return [found]
    return [sys.executable, "-m", "alembic"]


def test_alembic_upgrade_and_downgrade(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[2]
    source_ini = project_root / "alembic.ini"
    temp_ini = tmp_path / "alembic.ini"
    temp_db = tmp_path / "migration_smoke.db"

    contents = source_ini.read_text(encoding="utf-8")
    contents = contents.replace(
        "script_location = %(here)s/alembic",
        f"script_location = {project_root / 'alembic'}",
    )
    contents = contents.replace(
        "sqlalchemy.url = sqlite:///./iocvault.db",
        f"sqlalchemy.url = sqlite:///{temp_db}",
    )
    temp_ini.write_text(contents, encoding="utf-8")

    alembic = _alembic_cmd()
    upgrade = subprocess.run(
        [*alembic, "-c", str(temp_ini), "upgrade", "head"],
        cwd=project_root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert upgrade.returncode == 0, upgrade.stderr

    downgrade = subprocess.run(
        [*alembic, "-c", str(temp_ini), "downgrade", "base"],
        cwd=project_root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert downgrade.returncode == 0, downgrade.stderr
