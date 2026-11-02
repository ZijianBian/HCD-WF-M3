#!/bin/bash
# Bamboo CI script to build the actors needed by the regression tests, or reuse them from the cache
# Execute script from root directory
#
#   COMBO            combination of deps.yaml whose modules build and run all actors (required)
#   ACTORS           actor_install YAML names, e.g. "grayscale hcd_mergers"; when empty, the actors
#                    selected by the input_workflow.xml of the TESTS cases, plus hcd_mergers
#   TESTS            see st03-regression.sh, read when ACTORS is empty
#   ACTOR_VERSIONS   optional DIR=VERSION overrides applied on top of the components of deps.yaml,
#                    e.g. "grayscale=develop"
#   ACTOR_CACHE_ROOT cache location (default: /mnt/bamboo_deploy/HCD-WF/actor-cache on Bamboo,
#                    ~/.cache/hcd-wf-actors otherwise)
#   FORCE_REBUILD    set to 1 to rebuild even if the actor is cached
#   GIT_HTTP_TOKEN   HTTP access token for git.iter.org (default: $bamboo_HTTP_AUTH_BEARER_PASSWORD).
#                    When set, the ssh://git@git.iter.org/ URLs of the actor YAMLs are cloned over HTTPS,
#                    for agents without an SSH key
#
# The source of each actor is components.<DIR> of deps.yaml (repo + ref); a source DIR without a
# component keeps the VERSION of its actor_install YAML.
# An actor is cached per combination and module list, actor YAML content and resolved source commit,
# so a new commit on the branch or a different module list triggers a rebuild of that actor only.
# Writes actor_paths.env with the actor folders to put on PYTHONPATH.

source ./ci-sdcc/st00-header.sh || exit 1

# Note Disable set -e option when using on local as it will exit the shell on error
if [[ -n "${bamboo_buildKey:-}" ]]; then
    set -e -u -o pipefail
fi

ROOT_DIR=$(pwd)
DEPS_YAML="${DEPS_FILE:-$ROOT_DIR/deps.yaml}"

if [[ -z "${ACTORS:-}" ]]; then
    if [[ -z "${TESTS:-}" ]]; then
        echo "ERROR: Set ACTORS to a space-separated list of actor_install YAML names, or TESTS." >&2
        exit 1
    fi
    # The codes selected in the input_workflow.xml (input_workflow_reg.xml when HCDWF_TEST_MODE=1 and it
    # exists) of each case: setting value N > 0 picks the N-th name of its "list" attribute
    ACTORS=$(python3 - "$ROOT_DIR" "${HCDWF_TEST_MODE:-1}" $TESTS <<'EOF'
import os, sys
import xml.etree.ElementTree as ET
root, test_mode, tests = sys.argv[1], sys.argv[2], sys.argv[3:]
aliases = {"ascot_serial": "ascot", "ascot_parallel": "ascot", "bbnbi_serial": "ascot",
           "bbnbi_parallel": "ascot", "afsi": "ascot"}
actors = []
for test in tests:
    case = test.split(":", 1)[0]
    xml_file = os.path.join(root, "tests", "data", case, "input_workflow.xml")
    reg_file = xml_file[: -len(".xml")] + "_reg.xml"
    if test_mode == "1" and os.path.exists(reg_file):
        xml_file = reg_file
    for elem in ET.parse(xml_file).iter():
        names = elem.get("list")
        value = (elem.text or "").strip()
        if not names or not value.isdigit() or int(value) == 0:
            continue
        name = names.split()[int(value) - 1]
        name = aliases.get(name, name)
        if not os.path.exists(os.path.join(root, "actor_install", name + ".yml")):
            name = name.replace("_", "-")
        if not os.path.exists(os.path.join(root, "actor_install", name + ".yml")):
            sys.exit(f"ERROR: no actor_install YAML for {elem.tag}={value} ({name}) of {xml_file}")
        if name not in actors:
            actors.append(name)
if "hcd_mergers" not in actors:
    actors.append("hcd_mergers")
print(" ".join(actors))
EOF
) || exit 1
    echo "> ACTORS derived from TESTS: $ACTORS"
fi

if [[ -n "${bamboo_buildKey:-}" ]]; then
    ACTOR_CACHE_ROOT="${ACTOR_CACHE_ROOT:-/mnt/bamboo_deploy/HCD-WF/actor-cache}"
else
    ACTOR_CACHE_ROOT="${ACTOR_CACHE_ROOT:-${XDG_CACHE_HOME:-$HOME/.cache}/hcd-wf-actors}"
fi

# Clone over HTTPS with a token instead of SSH. GIT_CONFIG_* applies to every git command of this
# script and of actor_install.py, without writing the token to a git config file
GIT_HTTP_TOKEN="${GIT_HTTP_TOKEN:-${bamboo_HTTP_AUTH_BEARER_PASSWORD:-}}"
if [[ -n "$GIT_HTTP_TOKEN" ]]; then
    echo "> Using HTTPS with access token for git.iter.org"
    export GIT_CONFIG_COUNT=2
    export GIT_CONFIG_KEY_0="url.https://git.iter.org/scm/.insteadOf"
    export GIT_CONFIG_VALUE_0="ssh://git@git.iter.org/"
    export GIT_CONFIG_KEY_1="http.https://git.iter.org/.extraHeader"
    export GIT_CONFIG_VALUE_1="Authorization: Bearer $GIT_HTTP_TOKEN"
    # Fail instead of waiting for a password prompt
    export GIT_TERMINAL_PROMPT=0
fi
unset GIT_HTTP_TOKEN

umask 002

# Modules loaded by st00 (ci-deps/env.sh written by ci-sdcc/resolve_deps.sh)
LOADED_MODULES=$(sed -n 's/^module load //p' "${CI_DEPS_DIR:-$ROOT_DIR/ci-deps}/env.sh" | LC_ALL=C sort)
if [[ -z "$LOADED_MODULES" ]]; then
    echo "ERROR: no module list in ${CI_DEPS_DIR:-$ROOT_DIR/ci-deps}/env.sh" >&2
    exit 1
fi
MODULES_HASH=$(sha256sum <<< "$LOADED_MODULES" | cut -c1-12)
CACHE_DIR="$ACTOR_CACHE_ROOT/$COMBO-$MODULES_HASH"
mkdir -p "$CACHE_DIR"
echo "$LOADED_MODULES" > "$CACHE_DIR/modules.txt"
echo "> Actor cache: $CACHE_DIR"

# Print "DIR VCS REPO VERSION" for each source of a YAML, with the components of deps.yaml and
# then ACTOR_VERSIONS applied
list_sources() {
    python3 - "$1" "$DEPS_YAML" <<'EOF'
import os, sys, yaml
components = yaml.safe_load(open(sys.argv[2])).get("components") or {}
overrides = dict(s.split("=", 1) for s in os.environ.get("ACTOR_VERSIONS", "").split())
for s in yaml.safe_load(open(sys.argv[1])).get("SOURCES") or []:
    version = s["VERSION"]
    component = components.get(s["DIR"])
    if component:
        if component.get("repo") and component["repo"] != s["REPO"]:
            sys.exit(f"ERROR: components.{s['DIR']}.repo of {sys.argv[2]} is {component['repo']}, "
                     f"{sys.argv[1]} builds {s['REPO']}")
        version = str(component.get("ref") or version)
    print(s["DIR"], s["VCS"].lower(), s["REPO"], overrides.get(s["DIR"], version))
EOF
}

# Resolve a git branch or tag to its commit, commit hashes are returned unchanged
resolve_commit() {
    local repo=$1 version=$2 commit
    if [[ "$version" =~ ^[0-9a-f]{7,40}$ ]]; then
        echo "$version"
        return 0
    fi
    local refs
    if ! refs=$(git ls-remote "$repo" "refs/heads/$version" "refs/tags/$version" "refs/tags/$version^{}"); then
        echo "ERROR: cannot access $repo (check the SSH key, or set GIT_HTTP_TOKEN)" >&2
        return 1
    fi
    # For annotated tags the peeled ^{} entry is the commit
    commit=$(sort -k2 <<< "$refs" | tail -n 1 | cut -f1)
    if [[ -z "$commit" ]]; then
        echo "ERROR: $version not found in $repo" >&2
        return 1
    fi
    echo "$commit"
}

ACTOR_PATHS=""
for actor in $ACTORS; do
    yml="$ROOT_DIR/actor_install/$actor.yml"
    if [[ ! -f "$yml" ]]; then
        echo "ERROR: $yml does not exist" >&2
        exit 1
    fi

    # Pin every git source to a commit so the build matches the cache key
    key_input="$(sha256sum "$yml" | cut -d' ' -f1)"
    pins=()
    sources=$(list_sources "$yml") || exit 1
    while read -r src_dir vcs repo version; do
        if [[ "$vcs" == "git" ]]; then
            commit=$(resolve_commit "$repo" "$version") || exit 1
            pins+=(-V "$src_dir=$commit")
            key_input+=" $src_dir=$commit"
            echo "> $actor: $src_dir $version -> $commit"
        else
            key_input+=" $src_dir=$version"
        fi
    done <<< "$sources"

    dest="$CACHE_DIR/$actor-$(sha256sum <<< "$key_input" | cut -c1-12)"

    tmp="$dest.tmp.$$"
    # Every step is checked explicitly: set -e has no effect in a subshell followed by ||
    (
        # Only one build of the same actor at a time, a parallel job waits and reuses it
        flock 9 || exit 1
        if [[ -f "$dest/.complete" && -n "$(ls -A "$dest/actors" 2>/dev/null)" &&
              ! "${FORCE_REBUILD:-}" =~ ^([Tt]rue|1)$ ]]; then
            echo "> $actor: using cached build $dest"
            exit 0
        fi
        echo "> $actor: building into $dest"
        rm -rf "$tmp" && mkdir -p "$tmp/actors" || exit 1
        # ACTOR_VERSIONS is already resolved into the pins
        (cd "$tmp" && ACTOR_FOLDER="$tmp/actors" ACTOR_VERSIONS="" \
            python3 "$ROOT_DIR/actor_install/actor_install.py" --skipModules -p -D src "${pins[@]}" "$yml") || exit 1
        # Only a successful build is marked complete and moved into the cache
        echo "$key_input" > "$tmp/cache_key.txt" && touch "$tmp/.complete" || exit 1
        rm -rf "$dest" && mv -T "$tmp" "$dest" || exit 1
    ) 9>"$dest.lock" || {
        echo "ERROR: building $actor failed" >&2
        rm -rf "$tmp"
        exit 1
    }

    ACTOR_PATHS="$dest/actors${ACTOR_PATHS:+:$ACTOR_PATHS}"
done

echo "export ACTOR_PATHS=\"$ACTOR_PATHS\"" > actor_paths.env
echo "> Actor folders written to actor_paths.env"
cat actor_paths.env
echo "> Done"
