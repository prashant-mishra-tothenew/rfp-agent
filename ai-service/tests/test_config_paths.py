from pathlib import Path

from app.config import _REPO_ROOT, settings


def test_upload_dir_resolves_relative_to_repo_root():
    upload_dir = Path(settings.upload_dir).resolve()
    expected = (_REPO_ROOT / "data" / "uploads").resolve()
    assert upload_dir == expected
