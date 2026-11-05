"""Test setup: an isolated temp SQLite DB, created before any app module is imported."""
import os
import tempfile
from pathlib import Path

_tmp = Path(tempfile.mkdtemp(prefix="sta_tests_"))
os.environ["DATABASE_URL"] = f"sqlite:///{(_tmp / 'test.db').as_posix()}"
os.environ["JWT_SECRET"] = "test-secret-not-for-production-0123456789"
