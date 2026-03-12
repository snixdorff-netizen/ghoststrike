from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database_path: Path
    seed_data_path: Path
    auto_seed_demo: bool
    open_registration: bool
    bootstrap_admin_email: str | None
    bootstrap_admin_password: str | None


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_settings() -> Settings:
    return Settings(
        database_path=Path(os.getenv("ADA_IQ_DB_PATH", "data/ada_iq.db")),
        seed_data_path=Path(os.getenv("ADA_IQ_SEED_PATH", "src/ada_iq/data/demo_projects.json")),
        auto_seed_demo=_bool_env("ADA_IQ_AUTO_SEED", True),
        open_registration=_bool_env("ADA_IQ_OPEN_REGISTRATION", False),
        bootstrap_admin_email=os.getenv("ADA_IQ_BOOTSTRAP_ADMIN_EMAIL"),
        bootstrap_admin_password=os.getenv("ADA_IQ_BOOTSTRAP_ADMIN_PASSWORD"),
    )
