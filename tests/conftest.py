"""Root pytest config: caminhos, fixtures compartilhadas, markers globais."""
from __future__ import annotations

import os

# Em CI/local, garante variaveis minimas para imports de Settings se necessario.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://dba:x@localhost:5432/developer_brain")
os.environ.setdefault("JWT_SECRET", "test-secret-please-replace-me-12345678901234567890")
os.environ.setdefault("APP_ENV", "test")
