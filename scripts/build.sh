#!/usr/bin/env bash
set -euo pipefail

# Build .skill zip files from skill directories
# Usage: ./scripts/build.sh [skill-name]
#   If no skill name given, builds all skills.

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST_DIR="$REPO_ROOT/dist"
mkdir -p "$DIST_DIR"

build_skill() {
    local skill_dir="$1"
    local skill_name
    skill_name="$(basename "$skill_dir")"

    if [[ ! -f "$skill_dir/SKILL.md" ]]; then
        echo "SKIP: $skill_name (no SKILL.md found)"
        return
    fi

    local out="$DIST_DIR/$skill_name.skill"
    (cd "$REPO_ROOT" && zip -r -q "$out" "$skill_name/")
    echo "BUILT: $out"
}

if [[ $# -gt 0 ]]; then
    build_skill "$REPO_ROOT/$1"
else
    for dir in "$REPO_ROOT"/*/; do
        dir_name="$(basename "$dir")"
        [[ "$dir_name" == "template" || "$dir_name" == "scripts" || "$dir_name" == "dist" || "$dir_name" == ".claude-plugin" ]] && continue
        build_skill "$dir"
    done
fi
