#!/usr/bin/env bash
#
# Push ml-service to a Hugging Face Space.
#
# A Space is its own git repository, and Spaces cannot build from a
# subdirectory of another repo, so the service is mirrored rather than
# referenced. This repository stays the source of truth: run the script again
# after any change and the Space follows.
#
#   ./sync_to_space.sh <hf-username>/<space-name>
#
# Requires a Hugging Face access token with WRITE scope. Git will prompt for it
# as the password; the username is your HF username.
#
# What is NOT copied: model binaries (fetched at build time from the GitHub
# release), caches, and the Arpan-owned standalone detector, which is not part
# of the served API.

set -euo pipefail

SPACE="${1:-}"
if [[ -z "$SPACE" ]]; then
    echo "usage: ./sync_to_space.sh <hf-username>/<space-name>" >&2
    exit 1
fi

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

echo "→ cloning Space  https://huggingface.co/spaces/$SPACE"
git clone "https://huggingface.co/spaces/$SPACE" "$WORK/space"

echo "→ copying service files"
cd "$WORK/space"
# Clear tracked files so a deletion here propagates, but keep .git itself.
find . -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +

rsync -a \
    --exclude '__pycache__' \
    --exclude '.venv' \
    --exclude 'models/*' \
    --exclude '*.pt' --exclude '*.pkl' --exclude '*.joblib' \
    --exclude 'sync_to_space.sh' \
    --exclude 'SPACE_README.md' \
    --exclude '*_arpan*' --exclude '*_Arpan*' \
    "$HERE"/ ./

# The Space's README.md carries the YAML frontmatter that tells Hugging Face
# which SDK and port to use, so it replaces the service's own readme.
cp "$HERE/SPACE_README.md" ./README.md
mkdir -p models && touch models/.gitkeep

echo "→ files staged:"
git add -A
git status --short | sed 's/^/    /'

if git diff --cached --quiet; then
    echo "→ nothing changed; Space is already current"
    exit 0
fi

git -c user.email="noreply@bits-pilani.ac.in" \
    -c user.name="Team ARAJ" \
    commit -q -m "Sync ml-service from the project repository"

echo "→ pushing (git will ask for your HF username and a WRITE token)"
git push

echo "✓ pushed. Watch the build at https://huggingface.co/spaces/$SPACE"
echo "  When it is live, the API base is:"
echo "  https://$(echo "$SPACE" | tr '/' '-' | tr '[:upper:]' '[:lower:]').hf.space"
