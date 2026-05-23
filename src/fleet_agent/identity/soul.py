"""Identity loader — reads SOUL.md, NORTH_STAR.md, USER.md from identity/ directory.

Inspired by OpenClaw's agent workspace conventions: SOUL.md, IDENTITY.md, USER.md
are injected into the agent's context to define its personality and constraints.
"""

from pathlib import Path

from ..config import settings


class Identity:
    def __init__(self, identity_dir: Path | None = None) -> None:
        self._dir = identity_dir or settings.project_root / "identity"
        self._user_dir = Path.home() / ".fleet-agent" / "identity"
        self._user_dir.mkdir(parents=True, exist_ok=True)

    def _read_file(self, filename: str) -> str:
        # Check user override first, then project default
        user_path = self._user_dir / filename
        if user_path.exists():
            return user_path.read_text(encoding="utf-8")
        proj_path = self._dir / filename
        if proj_path.exists():
            return proj_path.read_text(encoding="utf-8")
        return ""

    @property
    def soul(self) -> str:
        return self._read_file("SOUL.md")

    @property
    def north_star(self) -> str:
        return self._read_file("NORTH_STAR.md")

    @property
    def user_info(self) -> str:
        return self._read_file("USER.md")

    def whoami(self) -> dict:
        name = settings.agent_name
        human = settings.human_name
        return {
            "name": name,
            "human": human,
            "soul_preview": self.soul[:300] + "..." if len(self.soul) > 300 else self.soul,
            "north_star_preview": (
                self.north_star[:200] + "..." if len(self.north_star) > 200
                else self.north_star
            ),
        }


def get_identity() -> Identity:
    return Identity()
