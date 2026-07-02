"""Configuration resolved from environment variables (and CLI overrides)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_MODEL = "claude-opus-4-8"
DEFAULT_EFFORT = "high"
VALID_EFFORTS = ("low", "medium", "high", "xhigh", "max")

# Skills that ship with this repository.
BUNDLED_SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in ("1", "true", "yes", "on")


@dataclass
class Config:
    model: str = DEFAULT_MODEL
    effort: str = DEFAULT_EFFORT
    max_tokens: int = 16000
    skills_dirs: list[Path] = field(default_factory=list)
    # Prompt y/N before running bash / writing / editing files.
    require_confirmation: bool = True
    workdir: Path = field(default_factory=Path.cwd)

    @classmethod
    def from_env(cls) -> "Config":
        skills_dirs = [BUNDLED_SKILLS_DIR]
        extra = os.environ.get("AI_AGENT_SKILLS_DIR")
        if extra:
            skills_dirs.append(Path(extra).expanduser())
        # A ./skills directory in the current project, if different from bundled.
        local = Path.cwd() / "skills"
        if local.resolve() not in [d.resolve() for d in skills_dirs if d.exists()]:
            skills_dirs.append(local)

        effort = os.environ.get("AI_AGENT_EFFORT", DEFAULT_EFFORT).lower()
        if effort not in VALID_EFFORTS:
            raise ValueError(
                f"AI_AGENT_EFFORT must be one of {VALID_EFFORTS}, got {effort!r}"
            )

        return cls(
            model=os.environ.get("AI_AGENT_MODEL", DEFAULT_MODEL),
            effort=effort,
            skills_dirs=skills_dirs,
            require_confirmation=not _truthy(os.environ.get("AI_AGENT_AUTO_APPROVE")),
        )


def build_client():
    """Create the Anthropic client, honoring corporate proxy settings.

    The bare Anthropic() constructor already resolves ANTHROPIC_API_KEY,
    ANTHROPIC_AUTH_TOKEN, an `ant auth login` profile, and ANTHROPIC_BASE_URL.
    We only add an explicit httpx proxy when HTTPS_PROXY is set so the SDK's
    default timeouts and connection limits are preserved.
    """
    import anthropic

    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    if proxy:
        from anthropic import DefaultHttpxClient

        return anthropic.Anthropic(http_client=DefaultHttpxClient(proxy=proxy))
    return anthropic.Anthropic()
