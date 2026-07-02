"""Tool definitions (JSON schema) and their local execution."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from ai_agent.config import Config
from ai_agent.skills import Skill

BASH_TIMEOUT_SECONDS = 120
MAX_OUTPUT_CHARS = 50_000

TOOL_DEFINITIONS = [
    {
        "name": "bash",
        "description": (
            "Run a shell command in the working directory and return combined "
            "stdout/stderr plus the exit code. Use for git, running tests, "
            "searching, or anything without a dedicated tool."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The shell command to run"},
            },
            "required": ["command"],
        },
    },
    {
        "name": "read_file",
        "description": "Read a text file relative to the working directory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to read"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Create or overwrite a text file relative to the working directory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to write"},
                "content": {"type": "string", "description": "Full file content"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "edit_file",
        "description": (
            "Replace an exact string in a file with a new string. The old string "
            "must appear exactly once."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to edit"},
                "old_string": {"type": "string", "description": "Exact text to replace"},
                "new_string": {"type": "string", "description": "Replacement text"},
            },
            "required": ["path", "old_string", "new_string"],
        },
    },
    {
        "name": "list_dir",
        "description": "List files and directories at a path relative to the working directory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory to list (default: .)"},
            },
            "required": [],
        },
    },
    {
        "name": "read_skill",
        "description": (
            "Load the full instructions of a skill by name. Call this before "
            "performing a task that one of the available skills covers."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Skill name from the skills index"},
            },
            "required": ["name"],
        },
    },
]

# Tools that mutate state and therefore ask for confirmation by default.
CONFIRM_TOOLS = {"bash", "write_file", "edit_file"}


class ToolError(Exception):
    """Raised by tool handlers; reported back to the model as is_error."""


class ToolExecutor:
    def __init__(self, config: Config, skills: dict[str, Skill]):
        self.config = config
        self.skills = skills

    # -- dispatch -----------------------------------------------------------

    def execute(self, name: str, tool_input: dict) -> tuple[str, bool]:
        """Run a tool. Returns (result_text, is_error)."""
        handler = getattr(self, f"_tool_{name}", None)
        if handler is None:
            return f"Unknown tool: {name}", True
        if name in CONFIRM_TOOLS and self.config.require_confirmation:
            if not self._confirm(name, tool_input):
                return "The user declined this action. Ask them how to proceed.", True
        try:
            return _truncate(handler(tool_input)), False
        except ToolError as exc:
            return str(exc), True
        except Exception as exc:  # surface unexpected failures to the model
            return f"{type(exc).__name__}: {exc}", True

    def _confirm(self, name: str, tool_input: dict) -> bool:
        preview = json.dumps(tool_input, ensure_ascii=False)
        if len(preview) > 300:
            preview = preview[:300] + "…"
        answer = input(f"\n[confirm] {name} {preview}\nRun this? [y/N] ")
        return answer.strip().lower() in ("y", "yes")

    # -- path safety --------------------------------------------------------

    def _resolve(self, raw: str) -> Path:
        path = (self.config.workdir / raw).resolve()
        if not path.is_relative_to(self.config.workdir.resolve()):
            raise ToolError(f"Path escapes the working directory: {raw}")
        return path

    # -- handlers ------------------------------------------------------------

    def _tool_bash(self, tool_input: dict) -> str:
        try:
            proc = subprocess.run(
                tool_input["command"],
                shell=True,
                cwd=self.config.workdir,
                capture_output=True,
                text=True,
                timeout=BASH_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            raise ToolError(f"Command timed out after {BASH_TIMEOUT_SECONDS}s")
        parts = []
        if proc.stdout:
            parts.append(proc.stdout)
        if proc.stderr:
            parts.append(f"[stderr]\n{proc.stderr}")
        parts.append(f"[exit code: {proc.returncode}]")
        return "\n".join(parts)

    def _tool_read_file(self, tool_input: dict) -> str:
        path = self._resolve(tool_input["path"])
        if not path.is_file():
            raise ToolError(f"Not a file: {tool_input['path']}")
        return path.read_text(encoding="utf-8")

    def _tool_write_file(self, tool_input: dict) -> str:
        path = self._resolve(tool_input["path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(tool_input["content"], encoding="utf-8")
        return f"Wrote {len(tool_input['content'])} chars to {tool_input['path']}"

    def _tool_edit_file(self, tool_input: dict) -> str:
        path = self._resolve(tool_input["path"])
        if not path.is_file():
            raise ToolError(f"Not a file: {tool_input['path']}")
        text = path.read_text(encoding="utf-8")
        old = tool_input["old_string"]
        count = text.count(old)
        if count == 0:
            raise ToolError("old_string not found in file")
        if count > 1:
            raise ToolError(f"old_string appears {count} times; make it unique")
        path.write_text(text.replace(old, tool_input["new_string"]), encoding="utf-8")
        return f"Edited {tool_input['path']}"

    def _tool_list_dir(self, tool_input: dict) -> str:
        path = self._resolve(tool_input.get("path") or ".")
        if not path.is_dir():
            raise ToolError(f"Not a directory: {tool_input.get('path', '.')}")
        entries = []
        for child in sorted(path.iterdir()):
            entries.append(child.name + ("/" if child.is_dir() else ""))
        return "\n".join(entries) or "(empty)"

    def _tool_read_skill(self, tool_input: dict) -> str:
        name = tool_input["name"]
        skill = self.skills.get(name)
        if skill is None:
            available = ", ".join(sorted(self.skills)) or "(none)"
            raise ToolError(f"No skill named {name!r}. Available: {available}")
        extras = [
            p.relative_to(skill.directory).as_posix()
            for p in sorted(skill.directory.rglob("*"))
            if p.is_file() and p.name != "SKILL.md"
        ]
        body = skill.body()
        if extras:
            listing = "\n".join(f"- {skill.directory / e}" for e in extras)
            body += f"\n\n[Bundled files in this skill you can read_file/bash]:\n{listing}"
        return body


def _truncate(text: str) -> str:
    if len(text) > MAX_OUTPUT_CHARS:
        return text[:MAX_OUTPUT_CHARS] + f"\n…[truncated {len(text) - MAX_OUTPUT_CHARS} chars]"
    return text
