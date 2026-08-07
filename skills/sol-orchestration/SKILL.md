---
name: sol-orchestration
description: "Cost-routed delegation for Prime Agent. Use when a task is large enough to split across delegated workers: the orchestrator keeps decomposition, specification, and acceptance, each child owns exactly one file set, and every boundary returns ship, fix-first, rethink, or abandon. Includes a manual procedure that runs without the Python module."
---

# Sol Orchestration

Act as the orchestrator. You own the objective, the decomposition, each child's
specification, and the acceptance decision. Children own implementation inside the
boundary you gave them, and nothing else.

This is the package skeleton. Routing, delegation transport, evidence capture, and
episodes are not implemented here — the Python module reports the environment and
this document carries the contract. Everything below is runnable by hand today, and
the manual procedure is not a fallback of last resort: it is the procedure, with the
Python call as a convenience on top.

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
