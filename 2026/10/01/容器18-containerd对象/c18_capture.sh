#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 || ! "$1" =~ ^[a-zA-Z0-9_.-]+$ || ! "$2" =~ ^[a-zA-Z0-9_.-]+$ || ! "$3" =~ ^[a-zA-Z0-9_.-]+$ ]]; then
    printf 'usage: %s OWN_NAMESPACE OWN_CONTAINER_ID STAGE\n' "$0" >&2
    exit 2
fi

namespace=$1
container_id=$2
stage=$3
repository=$(git rev-parse --show-toplevel)
lab_root="$repository/examples/containers/.lab-work/18"
mkdir -p "$lab_root"
test ! -L "$lab_root"
chmod 700 "$lab_root"
output=$(mktemp -d "$lab_root/$stage.XXXXXX")
printf 'output=%s\n' "$output"
printf 'stage=%s namespace=%s container_id=%s\n' "$stage" "$namespace" "$container_id" > "$output/receipt.txt"
date -u +%FT%TZ >> "$output/receipt.txt"
uname -sr >> "$output/receipt.txt"

record() {
    local label=$1
    shift
    printf '\nstart=%s command=' "$(date -u +%FT%TZ)" >> "$output/receipt.txt"
    printf '%q ' "$@" >> "$output/receipt.txt"
    printf '\n' >> "$output/receipt.txt"
    local result
    if "$@" > "$output/$label.stdout" 2> "$output/$label.stderr"; then
        result=0
    else
        result=$?
    fi
    printf 'end=%s exit=%s\n' "$(date -u +%FT%TZ)" "$result" >> "$output/receipt.txt"
}

record containerd-version containerd --version
record ctr-version ctr version
record image ctr --namespace "$namespace" images ls
record content ctr --namespace "$namespace" content ls
record snapshot ctr --namespace "$namespace" snapshots ls
record containers ctr --namespace "$namespace" containers ls
record container ctr --namespace "$namespace" containers info "$container_id"
record tasks ctr --namespace "$namespace" tasks ls
record task-processes ctr --namespace "$namespace" tasks ps "$container_id"

printf 'collection_end=%s; read receipt.txt before interpreting any empty output\n' "$(date -u +%FT%TZ)" >> "$output/receipt.txt"
