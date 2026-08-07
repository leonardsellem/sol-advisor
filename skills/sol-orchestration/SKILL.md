---
name: sol-orchestration
description: "Cost-routed delegation for Prime Agent. Use when a task is large enough to split across delegated workers: the orchestrator keeps decomposition, specification, and acceptance, each child owns exactly one file set, and every boundary returns ship, fix-first, rethink, or abandon. Includes a manual procedure that runs without the Python module."
---

# Sol Orchestration

Act as the orchestrator. You own the objective, the decomposition, each child's
specification, and the acceptance decision. Children own implementation inside the
boundary you gave them, and nothing else.

Preflight and routing are implemented. Delegation transport, evidence capture, and
episodes are not yet — this document carries the whole contract regardless.
Everything below is runnable by hand today, and the manual procedure is not a
fallback of last resort: it is the procedure, with the Python call as a convenience
on top.

## Check the environment first

From the kernel:

    print(await sol_orchestration())

Or with the interpreter and module path included:

    print(await sol_orchestration(verbose=True))

The report names the resolved Prime Agent home, the resolved kernel venv, the
variable that decided each, whether the environment is isolated from the operator's
real installation, and whether the bundled runtime is reachable.

### If the module is not there

Prime Agent binds a placeholder that raises `RuntimeError` when a Python skill fails
to import, and it installs nothing at all when `PRIME_AGENT_KERNEL_PYTHON` is set.
Both are **degradations, not failures** — say so out loud and keep going:

1. Report the degradation to the user in plain words: the Python module did not load,
   the environment check is unavailable, and orchestration continues manually.
2. Do not reinstall, rebuild the venv, or route around it silently.
3. Run the manual procedure below. It needs nothing from the module.

If the module loads but the runtime does not, `run()` says `runtime: degraded` and
names the import error rather than raising. Same three steps.

## Declare the allowlist before anything else

This package ships **no default allowlist and no default model**, anywhere. A default
would reintroduce a hardcoded model choice by being the value nobody ever edits. Every
model name in the system comes from one operator-owned file:

    <PRIME_AGENT_CODING_AGENT_DIR or ~/.prime/agent>/sol-orchestration/config.json

```json
{
  "allowlist": ["provider-a/model-one", "provider-a/model-two"],
  "review_model": "provider-a/model-two",
  "verification_commands": { "unit": ["python", "-m", "pytest", "-q"] },
  "routing_prior": {
    "default": "provider-a/model-one",
    "rules": [{ "domain": "python", "difficulty": "hard", "model": "provider-a/model-two" }]
  }
}
```

Every entry must be a full `provider/model` selector, because the spawn resolves an
exact `provider/id` match and a bare id can never resolve. `review_model` and every
model named in `routing_prior` must appear in the allowlist. A rule may use `"*"` as
its difficulty to match every difficulty in a domain; rules are tried in declared
order, so the operator controls precedence.

Removing this package is a delete of that directory. Nothing is written to Prime
Agent's own settings.

## Run preflight before every delegation

    report = await sol_orchestration.preflight.run()

It costs nothing. Model search resolves against credentials before any inference, and
the rest is file reads and read-only host requests. It either returns the surviving
allowlist or raises a refusal naming the artifact to change and the fix.

It **refuses** when:

- The config file is absent, malformed, or internally inconsistent.
- No declared entry survives the availability check. It never falls back to the
  session's own model — that model is the expensive orchestrator.
- The session's reasoning effort is below `high`. Nothing in the kernel can change
  the level, so it asks you to raise it with `/effort high` rather than pretending to.
- This session's children would not be retained. Only a retained child can receive a
  correction, so a session whose children carry no active session id is refused now
  rather than at correction time, after the child has been paid for.
- The agent-message or agent-observe host requests are unreachable. Correction
  delivery and child observation both route through them.

It **degrades and continues** when the effort level cannot be read, when some entries
were dropped, or when the runtime is not the version these contracts were verified
against. A routine patch bump must not halt the dataset. Every degradation is carried
in `report.degradations` and belongs in whatever you report afterwards.

Availability is resolved with **one query per declared entry**, never one catalog
enumeration. Model search is capped at twenty results; on a host with more
authenticated models than that, an enumeration silently reports authenticated entries
as unavailable — measured on this host at 8 of 28 wrongly dropped.

## Route each delegation

    decision = sol_orchestration.routing.select(
        domain=spec.domain, difficulty=spec.difficulty,
        prior=report.config.prior, surviving=report.surviving,
    )

Selection is a pure function of the declared features and the surviving set. A rule
naming a model that did not survive falls through to the next applicable rule; a
domain with no match takes the declared default; a spec missing a domain or a
difficulty is rejected rather than routed on a guess. `decision.surviving_size`
records how many candidates the choice was made from — choosing among four is not the
same event as choosing among one.

### Doing this by hand

With no Python: read the config file yourself, run `prime-agent model list` and drop
every declared entry that does not appear in it verbatim, confirm `/effort` is at
`high` or above, then apply the prior's rules in order against what survived. Refuse
in exactly the cases listed above rather than substituting a model.

## The delegation contract

Four rules. They hold in every lane, with or without the Python module.

### 1. One ownership set per child

Each child gets exactly one file set or one bounded responsibility, stated
explicitly. Two children never own the same file. Tell each child, in its own
specification, that it is not alone in the repository, that it must preserve edits it
did not make, and that it must adapt to concurrent changes rather than reverting
them.

Independent, non-overlapping children may run concurrently. Shared-file work and
dependency chains stay serial.

### 2. The orchestrator keeps decomposition and acceptance

Never delegate these:

- Resolving requirements and material ambiguity.
- Choosing the architecture, the interfaces, and the split into children.
- Writing each child's complete specification.
- Inspecting the actual diff and rerunning the verification commands yourself.
- Deciding whether the work is accepted.

Do not hand-write implementation code that a child could own. If a child returns
something wrong, fix the specification and delegate again — do not quietly repair the
patch yourself, and do not open a fresh child to escape an unresolved correction.

### 3. Every boundary returns exactly one outcome

A delegation boundary closes with one word, chosen by the orchestrator after
inspecting real evidence:

| Outcome | Meaning | What happens next |
| -- | -- | -- |
| `ship` | The work meets the specification and the evidence proves it. | Accept, and report with the evidence. |
| `fix-first` | The approach is right, the execution is not. | Re-specify the delta, delegate the fix, verify again, re-decide. |
| `rethink` | The specification or the architecture is wrong. | Revise the decomposition. Do not report completion. |
| `abandon` | The objective is not reachable on this path at acceptable cost. | Stop, state the wall in plain words, and hand the decision back. |

`abandon` is a real outcome, not a failure to be hidden. Choosing it early and
explicitly is cheaper than three rounds of `fix-first` against an objective that was
never reachable.

### 4. Claims are not evidence

A child's report is a claim. Before any outcome other than `abandon`:

1. Inspect the working tree and the complete diff.
2. Confirm only in-scope files changed.
3. Rerun the specification's verification commands yourself.
4. Compare what you observed against the objective, the interfaces, and the
   constraints you set.

## Manual procedure

Runnable by hand, with no Python module and no runtime.

1. **State the objective** in one sentence, and the acceptance test that proves it.
2. **Decompose** into children. For each child write down: the one file set it owns,
   its objective, its interfaces and constraints, and the exact command that verifies
   it. A child without a verification command is not specified yet.
3. **Order them.** Mark which children are independent (may run concurrently) and
   which are dependent (must be serial). Shared files force serial.
4. **Delegate one child at a time**, or one concurrent group at a time. Give the
   child its complete specification — a fresh worker inherits none of your context.
5. **Verify** with step 4 of the contract above: real diff, in-scope only, commands
   rerun by you.
6. **Close the boundary** with `ship`, `fix-first`, `rethink`, or `abandon`, and
   record which one and why.
7. **Repeat** until every child is closed, then re-run the acceptance test from step 1
   against the whole objective — not against the last child.

## Environment notes

- The Prime Agent home comes from `PRIME_AGENT_CODING_AGENT_DIR`, defaulting to
  `~/.prime/agent`.
- The kernel venv comes from `PRIME_AGENT_KERNEL_VENV`, defaulting to
  `~/.prime/agent/kernel-venv`. It is **not** derived from the home variable.
  Redirecting only the home does not isolate anything: an install will still land in,
  and rebuild, the operator's real kernel venv. Isolation requires both.
- `python -c "import sol_orchestration"` outside a kernel is expected to work. If it
  ever needs the kernel runtime to import, that is a defect — see
  `scripts/verify-prime-agent-package.sh` at the package root.
