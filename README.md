# AI-Agent

CLI tool-using AI agent powered by Claude — with a drop-in **skills** system
compatible with the `SKILL.md` convention (works with skills from
[thananon/9arm-skills](https://github.com/thananon/9arm-skills) and similar
collections).

เอเจนต์ AI แบบ CLI ที่ใช้ Claude API เรียกใช้เครื่องมือ (รันคำสั่ง shell,
อ่าน/เขียน/แก้ไฟล์) และโหลด "สกิล" จากโฟลเดอร์ `SKILL.md` ได้แบบเดียวกับ
Claude Code — เอาสกิลจาก repo อย่าง `9arm-skills` มาวางใช้ได้เลย

## Features / ความสามารถ

- **Tool-using agent loop** — Claude decides when to run `bash`, `read_file`,
  `write_file`, `edit_file`, `list_dir`; results stream back into the loop
  until the task is done.
- **Skills (progressive disclosure)** — only each skill's name + description
  is in the system prompt; the agent calls `read_skill` to load the full
  instructions when a task matches. Ships with a `scrutinize` skill for
  reviewing plans/PRs/code.
- **Safety confirmations** — `bash` / `write_file` / `edit_file` ask y/N
  before executing (disable with `-y` or `AI_AGENT_AUTO_APPROVE=1`).
  File tools are confined to the working directory.
- **Streaming + adaptive thinking** — default model `claude-opus-4-8` with
  `thinking: adaptive` and `effort: high`; system prompt is prompt-cached.

## Install / ติดตั้ง

```bash
git clone https://github.com/ttharkesm-admin01/AI-Agent.git
cd AI-Agent
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

Set your API key (or use `ant auth login` — the SDK picks up the profile):

```bash
cp .env.example .env   # then edit, or:
export ANTHROPIC_API_KEY=sk-ant-...
```

## Usage / วิธีใช้

```bash
# Interactive REPL / โหมดโต้ตอบ
ai-agent

# One-shot / สั่งครั้งเดียว
ai-agent "list the files here and summarize what this project does"

# List discovered skills / ดูสกิลทั้งหมด
ai-agent --list-skills

# Skip confirmations, pick model/effort
ai-agent -y --model claude-opus-4-8 --effort medium "run the tests and fix failures"
```

Example — use the bundled review skill / ตัวอย่างใช้สกิล `scrutinize`:

```bash
ai-agent "use the scrutinize skill to review the diff in my last commit"
```

## Adding skills / เพิ่มสกิล

A skill is a folder containing `SKILL.md` with YAML frontmatter:

```markdown
---
name: my-skill
description: When to use this skill (the agent reads this to decide).
---

Full instructions the agent follows after loading the skill...
```

Put skill folders in this repo's `skills/`, in `./skills` of whatever
directory you run `ai-agent` from, or point `AI_AGENT_SKILLS_DIR` at a
collection:

```bash
git clone https://github.com/thananon/9arm-skills ~/9arm-skills
export AI_AGENT_SKILLS_DIR=~/9arm-skills/skills
ai-agent --list-skills
```

Skill directories are scanned recursively, so category layouts like
`skills/engineering/scrutinize/SKILL.md` work. On name collisions the
later directory wins (user skills override bundled ones).

## Corporate network (e.g. CPF office) / ใช้ในเน็ตบริษัท

ถ้าเครื่องบริษัทต้องออกเน็ตผ่าน proxy ให้ตั้งค่า:

```bash
export HTTPS_PROXY=http://proxy.your-company.com:8080
# ถ้าบริษัทมี gateway ภายในสำหรับ Anthropic API:
export ANTHROPIC_BASE_URL=https://your-internal-gateway.example.com
```

The client is built with the SDK's `DefaultHttpxClient(proxy=...)` so default
timeouts/retries are preserved. If TLS interception is used on your network,
set `SSL_CERT_FILE` to your company CA bundle.

> หมายเหตุ: อย่า commit ไฟล์ `.env` (มี API key) — มันถูก ignore ไว้แล้วใน
> `.gitignore` และควรตรวจนโยบายการใช้ AI ของบริษัทก่อนใช้กับข้อมูลภายใน

## Configuration / ตัวแปรทั้งหมด

| Env var | Default | Meaning |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | API key (or use an `ant auth login` profile) |
| `AI_AGENT_MODEL` | `claude-opus-4-8` | Model ID |
| `AI_AGENT_EFFORT` | `high` | `low` / `medium` / `high` / `xhigh` / `max` |
| `AI_AGENT_SKILLS_DIR` | — | Extra skills directory |
| `AI_AGENT_AUTO_APPROVE` | off | `1` = don't ask y/N before bash/write/edit |
| `HTTPS_PROXY` | — | Corporate proxy |
| `ANTHROPIC_BASE_URL` | — | Alternate API endpoint / internal gateway |

## Development / พัฒนา

```bash
pip install -e ".[dev]"
pytest            # unit tests need no API key
```

Project layout:

```
ai_agent/
  agent.py    # streaming agentic loop (tool_use -> execute -> tool_result)
  tools.py    # tool schemas + local execution, path confinement, confirmations
  skills.py   # SKILL.md discovery + frontmatter parsing
  config.py   # env-driven config, proxy-aware client factory
  cli.py      # REPL / one-shot / --list-skills
skills/
  scrutinize/ # bundled review skill
tests/
```
