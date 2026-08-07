# plugins/sol-advisor

The Codex plugin. A primary Sol session owns architecture, decomposition, verification
and acceptance; bounded implementation goes to a native Terra custom-agent thread, or to
a user-visible Luna app task when the user explicitly opts in per request.

Full user-facing documentation is in the [repository README](../../README.md). This file
is a map for people already in the directory.

## Contents

| Path | Purpose |
|---|---|
| `.codex-plugin/plugin.json` | Plugin manifest |
| `agents/` | Terra implementer and Sol reviewer role pins (user-owned files) |
| `scripts/verify.sh` | Verifier — disposable targets, never mutates Codex configuration |
| `scripts/install-agents.sh` | Installs and byte-checks the companion roles |
| `scripts/inspect-agent-runtime.sh` | Read-only routing-evidence fallback |
| `skills/orchestration/` | The orchestration skill and its references |

## Quick reference

```sh
sh plugins/sol-advisor/scripts/verify.sh                    # validate
sh plugins/sol-advisor/scripts/install-agents.sh --check    # byte-exact role check
```

## A note for contributors on the fork

This directory is inherited from the repository this one was forked from, and is
deliberately kept byte-identical to it apart from this README and `AGENTS.md`. Run
`git remote get-url upstream` to see which repository that is for your checkout.

The fork's own work lives in `skills/sol-orchestration/` — a separate Prime Agent
capability package that shares no code with this plugin.
