#!/usr/bin/env bash
set -xueo pipefail

rm -rf .packed
mkdir .packed

for charmdir in test-kubernetes test-machine; do
    TMPDIR=".$charmdir"
    rm -rf "$TMPDIR"
    cp --recursive "$charmdir" "$TMPDIR"
    unlink "$TMPDIR/src/common.py"  # remove symlink
    cp common/src/common.py "$TMPDIR/src/"
    cp common/requirements.txt "$TMPDIR/"
    cat common/actions.yaml >> "$TMPDIR/charmcraft.yaml"
    mkdir "$TMPDIR/pathops"
    cp -r ../../../../pyproject.toml "$TMPDIR/pathops/"
    cp -r ../../../../src "$TMPDIR/pathops/"
    cd "$TMPDIR"
    charmcraft pack
    mv *.charm ../.packed/
    cd -
    rm -rf "$TMPDIR"
done

echo .packed/*.charm
