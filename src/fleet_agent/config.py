"""Configuration via pydantic-settings."""

from pathlib import Path

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
    db_path: Path = data_dir / "fleet-agent.db"

    # Agent identity
    agent_name: str = "Fritz"
    human_name: str = "Sandra"

    # Heartbeat
    heartbeat_enabled: bool = False
    heartbeat_interval_minutes: int = 30

    # Agent step (SFB brain tier): cline-mcp REST endpoint + local model
    cline_mcp_url: str = "http://127.0.0.1:11103"
    cline_mcp_provider: str = "ollama"
    cline_mcp_model: str = "muse-glimmer"
    cline_mcp_timeout_s: float = 300.0

    # Fleet registry (mcp-federation-hub bridge) for dynamic server discovery
    fleet_hub_url: str = "http://127.0.0.1:10857"

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.joinpath("cards").mkdir(parents=True, exist_ok=True)
        self.data_dir.joinpath("projects").mkdir(parents=True, exist_ok=True)
        self.data_dir.joinpath("evolution").mkdir(parents=True, exist_ok=True)
        self.data_dir.joinpath("artifacts").mkdir(parents=True, exist_ok=True)


settings = Settings()
