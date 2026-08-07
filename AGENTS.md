# sol-advisor — repository conventions

Two orchestration contracts live here, one per harness. They share a discipline and
nothing else. **Load exactly one, decided by the harness you are running in.**

| You are | Read | Never touch |
|---|---|---|
| Codex | `plugins/sol-advisor/` | `package.json`, `skills/`, `scripts/` |
| Prime Agent | `skills/sol-orchestration/` | `plugins/`, `.agents/` |

A session that loads the wrong contract will produce plausible work against the wrong
runtime. If it is ambiguous, ask rather than guess.

## The rule that outranks the rest

**`plugins/` and `.agents/` are inherited, not ours.** They are the Codex plugin and its
marketplace manifest, and the Prime Agent work in `skills/` is built on the standing
evidence that installing it changes neither.

When this repository is a fork, that inheritance is literal. Resolve who from the
checkout rather than from memory — the answer differs per fork and this file travels:

```sh
git remote get-url upstream 2>/dev/null || echo "no upstream remote configured"
```

Before opening a PR that touches anything else:

```sh
git diff origin/main -- plugins .agents    # must be empty
```

If the Codex plugin verifier fails for a reason you did not cause, file it as its own
issue and fix it in its own PR. Folding that fix into a feature PR destroys the
byte-identity that PR asserts.

## Root footprint is three paths

`package.json`, `skills/`, `scripts/`. That was an explicit, costed decision — a fork's
root is the most likely place to collide on an upstream merge. Do not add a fourth
without deciding to.

## Verify before claiming anything

```sh
jq empty package.json
sh scripts/verify-prime-agent-package.sh     # 19 checks, Prime Agent package
sh plugins/sol-advisor/scripts/verify.sh     # Codex plugin
git diff --check
```

Neither verifier mutates host configuration or starts an interactive session. Run them;
do not reason about whether they would pass.

## Working on the Prime Agent package

```sh
cd skills/sol-orchestration
uv run --with pytest python -m pytest -q
uv run --python 3.14 --with pytest python -m pytest -q -W error
uv run --python 3.11 --with pytest python -m pytest -q -W error
```

Run more than one interpreter. `uv` resolves different Pythons in different worktrees,
and a suite green on one can warn on another.

Anything that installs or starts a session needs **both** isolation variables:

```sh
export PRIME_AGENT_CODING_AGENT_DIR=$(mktemp -d)
export PRIME_AGENT_KERNEL_VENV=$(mktemp -d)/kernel-venv
cp ~/.prime/agent/auth.json "$PRIME_AGENT_CODING_AGENT_DIR/"
```

Redirecting only the home is **not** isolation: the runtime resolves the kernel venv
from its own variable and otherwise from a path hardcoded off the real user home, so a
half-redirected run rebuilds the operator's real venv while looking disposable.

Compare a real home by **path and size**, never by a hash including mtimes — unrelated
prime-agent activity moves an mtime-inclusive hash with no content change, and a
tripwire that cries wolf gets ignored.

## Conventions that are not negotiable here

- **Never declare `prime-agent-runtime` as a dependency.** It ships with Prime Agent and
  is not on PyPI. Import `rlm` lazily inside the call; a module-level import fails the
  verifier and a test.
- **No model name in package source.** A test scans every module. The allowlist and the
  routing prior belong to the operator's config file, never to the code.
- **No thinking or effort host request.** No handler exists; a call would fail at best
  and silently no-op at worst. The verifier fails the build on any such call site.
- **Nothing is enforced.** The kernel is a durable control environment, not a sandbox.
  Child constraints are prompt text and the ownership set is a detection device. Do not
  write a doc, a comment, or a commit message that implies otherwise.

## Pull requests

**`gh` resolves a fork to its parent.** `gh repo view --json nameWithOwner` returns the
*upstream* slug, not this checkout's, so a bare `gh pr create` targets upstream and fails
with "No commits between main and …". Derive from `origin`, which is authoritative:

```sh
repo=$(git remote get-url origin | sed -E 's#^(git@|ssh://git@|https://)github\.com[:/]##; s#\.git$##')
gh pr create --repo "$repo" --base main --head "$(git branch --show-current)"
```

That derivation is the reason no document in this repository hardcodes an owner/repo
slug: the same command then works here, upstream, and in any fork, with no edit. The one
declared exception is `.repository.url` in `package.json`, and
`scripts/verify-prime-agent-package.sh` fails the build when it disagrees with `origin`
— so a fork is told once, loudly, rather than shipping someone else's URL quietly.

`main` is read-only — work in a worktree off `origin/main`, never check a feature branch
out in the canonical clone.

## Where to go next

- `skills/AGENTS.md` — the Prime Agent skills directory
- `skills/sol-orchestration/AGENTS.md` — the package itself
- `scripts/AGENTS.md` — the verifiers
- `plugins/sol-advisor/AGENTS.md` — the Codex plugin

<!-- auto-generated by lp-repo-docs-update — review and enrich -->
<!-- doc-watermark: d0d2342 -->
