#!/usr/bin/env bash
set -xueo pipefail

mkdir --parents .packed

CHARMS=()
for charm in test-kubernetes test-machine; do
    cp --recursive "$charm" ".$charm"
    unlink ".$charm/src/common.py"  # remove symlink
    cp common/src/common.py ".$charm/src/"
    cp common/requirements.txt ".$charm/"
    cat common/actions.yaml >> ".$charm/charmcraft.yaml"
    cd ".$charm"
    charmcraft pack
    cd -
    PACKED=$(basename ".$charm/*.charm")
    mv ".$charm/*.charm" ".packed/"
    CHARMS+=".packed/$PACKED"
    rm -rf ".$charm"
done
echo ${CHARMS[@]}
