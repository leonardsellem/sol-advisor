# skills/

Skills Prime Agent discovers from this repository. `package.json` points `pi.skills`
here, so anything added becomes discoverable.

Invisible to Codex — Codex reads `plugins/sol-advisor/`.

## Contents

| Skill | What it is |
|---|---|
| [`sol-orchestration/`](sol-orchestration/) | Cost-routed delegation. A markdown contract that stands alone, plus a Python package the kernel installs so the deterministic parts run for free. |

## Adding a skill

Three names must agree or the skill silently degrades to markdown: the directory name,
the `name:` in its `SKILL.md` frontmatter, and the Python import identifier (hyphens
become underscores). Run `sh ../scripts/verify-prime-agent-package.sh` after any rename —
Prime Agent will not tell you.
