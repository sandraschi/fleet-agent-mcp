"""Configuration via pydantic-settings."""

from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="FLEET_AGENT_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    host: str = "127.0.0.1"
    port: int = 10996
    transport: str = "http"

    # Paths
    project_root: Path = Path(__file__).resolve().parent.parent.parent
    data_dir: Path = Path.home() / ".fleet-agent"
    memory_dir: Path = Path("memory")
    workflows_dir: Path = Path("workflows")
    identity_dir: Path = Path("identity")
    db_path: Path | None = None

    @model_validator(mode="after")
    def _derive_paths(self) -> "Settings":
        # See src/fleet_agent/config.py for the full explanation. Short version:
        # `db_path = data_dir / "fleet-agent.db"` in the class body is evaluated
        # once at class-definition time against the DEFAULT data_dir, so an
        # FLEET_AGENT_DATA_DIR override moves data_dir but leaves db_path behind.
        if self.db_path is None:
            object.__setattr__(self, "db_path", self.data_dir / "fleet-agent.db")
        return self

    # Agent identity
    agent_name: str = "Fritz"
    human_name: str = "Sandra"

    # Heartbeat
    heartbeat_enabled: bool = False
    heartbeat_interval_minutes: int = 30

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.joinpath("cards").mkdir(parents=True, exist_ok=True)
        self.data_dir.joinpath("projects").mkdir(parents=True, exist_ok=True)
        self.data_dir.joinpath("evolution").mkdir(parents=True, exist_ok=True)
        self.data_dir.joinpath("artifacts").mkdir(parents=True, exist_ok=True)


settings = Settings()
