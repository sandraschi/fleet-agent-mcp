"""Fleet Intel Reports Hub — shared HTML reports for Fritz + AIWatcher."""

from .client import publish_to_hub
from .store import publish_report

__all__ = ["publish_report", "publish_to_hub"]
