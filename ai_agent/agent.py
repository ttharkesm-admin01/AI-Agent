"""The agentic loop: stream Claude's response, execute tools, repeat."""

from __future__ import annotations

from ai_agent.config import Config, build_client
from ai_agent.skills import Skill, discover_skills
from ai_agent.tools import TOOL_DEFINITIONS, ToolExecutor

SYSTEM_PROMPT = """\
You are AI-Agent, a capable assistant running in a terminal with access to \
the user's working directory: {workdir}

Principles (after Karpathy's guidelines):
- Think before coding: surface assumptions; ask when the request is ambiguous.
- Simplicity first: prefer the smallest change that works.
- Surgical changes: edit only what's necessary; don't refactor unasked.
- Goal-driven: verify your work (run the code or tests) before declaring done.

Tools: use bash/read_file/write_file/edit_file/list_dir to act on the system. \
Parse and act on real output — never fabricate results.

Skills: task-specific playbooks are available. When a task matches a skill's \
description, call read_skill with its name FIRST and follow its instructions.

Available skills:
{skills_index}
"""


def format_skills_index(skills: dict[str, Skill]) -> str:
    if not skills:
        return "(no skills installed)"
    lines = []
    for name in sorted(skills):
        desc = skills[name].description or "(no description)"
        lines.append(f"- {name}: {desc}")
    return "\n".join(lines)


class Agent:
    def __init__(self, config: Config, quiet: bool = False):
        self.config = config
        self.quiet = quiet
        self.client = build_client()
        self.skills = discover_skills(config.skills_dirs)
        self.executor = ToolExecutor(config, self.skills)
        self.messages: list[dict] = []
        self.system_prompt = SYSTEM_PROMPT.format(
            workdir=config.workdir,
            skills_index=format_skills_index(self.skills),
        )

    def run_turn(self, user_message: str) -> str:
        """Send one user message, run tools until the model finishes.

        Returns the final text of the turn (it is also streamed to stdout).
        """
        self.messages.append({"role": "user", "content": user_message})
        final_text = ""

        while True:
            with self.client.messages.stream(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                system=[
                    {
                        "type": "text",
                        "text": self.system_prompt,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                thinking={"type": "adaptive"},
                output_config={"effort": self.config.effort},
                tools=TOOL_DEFINITIONS,
                messages=self.messages,
            ) as stream:
                for text in stream.text_stream:
                    final_text += text
                    print(text, end="", flush=True)
                response = stream.get_final_message()

            # Preserve full content (incl. thinking/tool_use blocks) in history.
            self.messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "refusal":
                note = "\n[the model declined this request for safety reasons]"
                print(note)
                return final_text + note

            if response.stop_reason == "pause_turn":
                continue  # server-side pause; re-send to resume

            if response.stop_reason != "tool_use":
                print()
                return final_text

            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                if not self.quiet:
                    print(f"\n[tool] {block.name}", flush=True)
                result, is_error = self.executor.execute(block.name, dict(block.input))
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                        "is_error": is_error,
                    }
                )
            # All results for the turn go back in ONE user message.
            self.messages.append({"role": "user", "content": tool_results})
