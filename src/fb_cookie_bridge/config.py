from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class Settings:
    cookie_file: Path
    host: str = "0.0.0.0"
    port: int = 8899
    impersonate: str = "chrome"
    timeout_seconds: int = 30

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            cookie_file=Path(os.environ.get("FBCB_COOKIE_FILE", "/run/secrets/facebook_cookies.json")),
            host=os.environ.get("FBCB_HOST", "0.0.0.0"),
            port=int(os.environ.get("FBCB_PORT", "8899")),
            impersonate=os.environ.get("FBCB_IMPERSONATE", "chrome"),
            timeout_seconds=int(os.environ.get("FBCB_TIMEOUT_SECONDS", "30")),
        )
