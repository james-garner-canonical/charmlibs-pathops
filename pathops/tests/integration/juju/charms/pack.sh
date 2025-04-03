#!/usr/bin/env bash
# usage: pack.sh machine|kubernetes [charmcraft args]
# e.g. pack.sh kubernetes --destructive-mode
set -xueo pipefail

rm -rf .packed
mkdir .packed

CHARMDIR="test-$1"  # test-machine or test-kubernetes
shift 1  # we'll pass the remaining args to charmcraft pack

TMPDIR=".$CHARMDIR"
rm -rf "$TMPDIR"

cp --recursive "$CHARMDIR" "$TMPDIR"
unlink "$TMPDIR/src/common.py"  # remove symlink
cp common/src/common.py "$TMPDIR/src/"
cp common/pyproject.toml "$TMPDIR/"
cat common/actions.yaml >> "$TMPDIR/charmcraft.yaml"
mkdir "$TMPDIR/pathops"
cp -r ../../../../pyproject.toml "$TMPDIR/pathops/"
cp -r ../../../../src "$TMPDIR/pathops/"

cd "$TMPDIR"
uv lock
charmcraft pack "$@"
cd -

mv "$TMPDIR"/*.charm .packed/
rm -rf "$TMPDIR"
