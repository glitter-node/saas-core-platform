#!/usr/bin/env bash
set -e

cd "$(git rev-parse --show-toplevel)"

TYPE=${1:-patch}

if [ ! -f VERSION ]; then
echo "0.1.0" > VERSION
fi

if ! git diff --quiet || ! git diff --cached --quiet; then
echo "working tree not clean"
exit 1
fi

VERSION=$(cat VERSION)
IFS='.' read -r MAJOR MINOR PATCH <<< "$VERSION"

case "$TYPE" in
patch)
PATCH=$((PATCH+1))
;;
minor)
MINOR=$((MINOR+1))
PATCH=0
;;
major)
MAJOR=$((MAJOR+1))
MINOR=0
PATCH=0
;;
*)
echo "usage: bump_version.sh [patch|minor|major]"
exit 1
;;
esac

NEW_VERSION="$MAJOR.$MINOR.$PATCH"
BRANCH=$(git rev-parse --abbrev-ref HEAD)

if git rev-parse "v$NEW_VERSION" >/dev/null 2>&1; then
echo "tag v$NEW_VERSION already exists"
exit 1
fi

echo "$NEW_VERSION" > VERSION

git add VERSION
git commit -m "release v$NEW_VERSION"

git tag -a "v$NEW_VERSION" -m "release v$NEW_VERSION"

git push origin "$BRANCH"
git push origin "v$NEW_VERSION"

echo "released v$NEW_VERSION"
