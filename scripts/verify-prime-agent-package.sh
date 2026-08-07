#!/bin/sh
# Structural verifier for the Prime Agent capability package.
#
# Prime Agent is lenient by design: a broken manifest entry, a frontmatter name that
# disagrees with its directory, or a hatch wheel-packages list that disagrees with the
# source directory does not raise. The skill just degrades to markdown, or vanishes
# from discovery, behind a load warning nobody reads. This script is what makes those
# failures loud. It checks structure only — it never installs, never starts a session,
# and never touches the operator's Prime Agent home or kernel venv.
#
# Usage: sh scripts/verify-prime-agent-package.sh [package-root]
# Exit:  0 when every check passes; 1 otherwise, naming each offending file.

set -u

ROOT=${1:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}
MANIFEST="$ROOT/package.json"

failures=0
checks=0

fail() {
	failures=$((failures + 1))
	printf 'FAIL %s: %s\n' "$1" "$2" >&2
}

pass() {
	checks=$((checks + 1))
	printf 'ok   %s\n' "$1"
}

require_command() {
	if ! command -v "$1" >/dev/null 2>&1; then
		printf 'FAIL %s: required command not found; install it and re-run\n' "$1" >&2
		exit 1
	fi
}

require_command jq

# --- manifest -----------------------------------------------------------------

if [ ! -f "$MANIFEST" ]; then
	fail "$MANIFEST" "root package.json is missing; Prime Agent cannot install this as a package"
	printf '\n%d check(s) passed, %d failed\n' "$checks" "$failures" >&2
	exit 1
fi

if ! jq empty "$MANIFEST" >/dev/null 2>&1; then
	fail "$MANIFEST" "not valid JSON: $(jq empty "$MANIFEST" 2>&1 | head -1)"
	printf '\n%d check(s) passed, %d failed\n' "$checks" "$failures" >&2
	exit 1
fi
pass "$MANIFEST parses as JSON"

if [ "$(jq -r '(.keywords // []) | index("pi-package") | if . == null then "no" else "yes" end' "$MANIFEST")" = "yes" ]; then
	pass "$MANIFEST declares the pi-package keyword"
else
	fail "$MANIFEST" 'keywords must contain "pi-package" for package discoverability'
fi

skill_roots=$(jq -r '.pi.skills // [] | .[]' "$MANIFEST")
if [ -z "$skill_roots" ]; then
	fail "$MANIFEST" 'pi.skills must list at least one skills directory (for example ["./skills"])'
else
	pass "$MANIFEST declares pi.skills"
fi

if [ "$(jq -r '(.dependencies // {}) | length' "$MANIFEST")" != "0" ]; then
	fail "$MANIFEST" "declares npm dependencies; this package must install with no dependency graph"
else
	pass "$MANIFEST declares no npm dependencies"
fi

# --- skill directories --------------------------------------------------------

skill_dirs=""
for entry in $skill_roots; do
	resolved="$ROOT/${entry#./}"
	if [ ! -d "$resolved" ]; then
		fail "$MANIFEST" "pi.skills entry '$entry' does not resolve to a directory ($resolved)"
		continue
	fi
	pass "pi.skills entry '$entry' resolves to $resolved"
	found=$(find "$resolved" -name SKILL.md -type f | sort)
	if [ -z "$found" ]; then
		fail "$resolved" "contains no SKILL.md; nothing would be discovered from this entry"
		continue
	fi
	skill_dirs="$skill_dirs$(printf '%s\n' "$found" | sed 's:/SKILL.md$::')
"
done

frontmatter_value() {
	# $1 = SKILL.md path, $2 = key. Prints the raw scalar value, quotes stripped.
	awk -v key="$2" '
		NR == 1 { if ($0 != "---") exit 1; next }
		/^---[[:space:]]*$/ { exit }
		{
			split($0, parts, ":")
			k = parts[1]
			gsub(/^[[:space:]]+|[[:space:]]+$/, "", k)
			if (k == key) {
				value = substr($0, index($0, ":") + 1)
				gsub(/^[[:space:]]+|[[:space:]]+$/, "", value)
				gsub(/^"|"$/, "", value)
				gsub(/^'\''|'\''$/, "", value)
				print value
				exit
			}
		}
	' "$1"
}

for skill_dir in $skill_dirs; do
	[ -n "$skill_dir" ] || continue
	skill_md="$skill_dir/SKILL.md"
	dir_name=$(basename "$skill_dir")

	if ! head -1 "$skill_md" | grep -q '^---[[:space:]]*$'; then
		fail "$skill_md" "must open with a YAML frontmatter block delimited by ---"
		continue
	fi

	name=$(frontmatter_value "$skill_md" name)
	description=$(frontmatter_value "$skill_md" description)

	if [ -z "$name" ]; then
		fail "$skill_md" "frontmatter has no name"
		continue
	fi

	if [ "$name" != "$dir_name" ]; then
		fail "$skill_md" "frontmatter name '$name' disagrees with its directory '$dir_name'; Prime Agent warns and the detection contract breaks"
	else
		pass "$skill_md name matches its directory ($name)"
	fi

	if printf '%s' "$name" | grep -Eq '^[a-z0-9]+(-[a-z0-9]+)*$'; then
		pass "$skill_md name '$name' satisfies the Agent Skills name rules"
	else
		fail "$skill_md" "name '$name' must be lowercase a-z, 0-9 and single internal hyphens only"
	fi

	if [ "${#name}" -gt 64 ]; then
		fail "$skill_md" "name is ${#name} characters; the specification allows at most 64"
	fi

	if [ -z "$description" ]; then
		fail "$skill_md" "frontmatter has no description; Prime Agent refuses to load a skill without one"
	elif [ "${#description}" -gt 1024 ]; then
		fail "$skill_md" "description is ${#description} characters; the specification allows at most 1024"
	else
		pass "$skill_md has a description within the 1024-character limit"
	fi

	# --- Python-backed detection contract -------------------------------------

	pyproject="$skill_dir/pyproject.toml"
	if [ ! -f "$pyproject" ]; then
		pass "$skill_md is a markdown-only skill (no pyproject.toml, nothing further to check)"
		continue
	fi

	import_name=$(printf '%s' "$name" | tr '-' '_')
	if ! printf '%s' "$import_name" | grep -Eq '^[a-z_][a-z0-9_]*$'; then
		fail "$pyproject" "import name '$import_name' derived from '$name' is not a valid Python identifier"
		continue
	fi

	init_py="$skill_dir/src/$import_name/__init__.py"
	if [ -f "$init_py" ]; then
		pass "$init_py exists (src layout matches the import name)"
	else
		fail "$pyproject" "expected src/$import_name/__init__.py for skill '$name'; without it the skill silently degrades to markdown"
	fi

	if grep -Eq "packages[[:space:]]*=[[:space:]]*\[[[:space:]]*[\"']src/$import_name[\"']" "$pyproject"; then
		pass "$pyproject wheel packages match src/$import_name"
	else
		declared=$(grep -E '^[[:space:]]*packages[[:space:]]*=' "$pyproject" | head -1 | sed 's/^[[:space:]]*//')
		fail "$pyproject" "[tool.hatch.build.targets.wheel] packages must be [\"src/$import_name\"]; found ${declared:-nothing}"
	fi

	# Only meaningful when the module is where the contract says it is; a missing
	# module has already been reported above and would report twice otherwise.
	if [ -f "$init_py" ]; then
		if grep -Eq '^[[:space:]]*(async[[:space:]]+)?def[[:space:]]+run[[:space:]]*\(' "$init_py"; then
			pass "$init_py defines run(), so the kernel exposes the module as a callable"
		else
			fail "$init_py" "defines no run(); the module would be imported but not callable in the kernel"
		fi
	fi

	if sed -n '/^dependencies[[:space:]]*=/,/\]/p' "$pyproject" | grep -q 'prime-agent-runtime'; then
		fail "$pyproject" "declares prime-agent-runtime as a dependency; it is bundled with Prime Agent, not published, and declaring it breaks every install outside the kernel venv"
	else
		pass "$pyproject does not declare the bundled runtime as a dependency"
	fi

	offenders=$(find "$skill_dir/src" -name '*.py' -type f 2>/dev/null | sort | while read -r module; do
		if grep -Eq '^(import|from)[[:space:]]+rlm([[:space:]]|\.|$)' "$module"; then
			printf '%s ' "$module"
		fi
	done)
	if [ -n "$offenders" ]; then
		fail "$(printf '%s' "$offenders" | sed 's/ $//')" "imports the bundled runtime at module level; import it lazily inside the call so the module still imports outside a kernel"
	else
		pass "$skill_dir/src has no module-level import of the bundled runtime"
	fi
done

printf '\n%d check(s) passed, %d failed\n' "$checks" "$failures"
[ "$failures" -eq 0 ] || exit 1
