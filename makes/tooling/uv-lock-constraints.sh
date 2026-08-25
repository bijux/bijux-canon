#!/bin/sh

set -eu

repository_root=$1
output_file=$2
output_directory=$(dirname "$output_file")
temporary_file="${output_file}.tmp.$$"

mkdir -p "$output_directory"
trap 'rm -f "$temporary_file"' EXIT HUP INT TERM

uv export \
    --quiet \
    --project "$repository_root" \
    --frozen \
    --group dev \
    --no-emit-project \
    --no-emit-workspace \
    --no-hashes \
    --no-annotate \
    --no-header \
    --output-file "$temporary_file"
mv "$temporary_file" "$output_file"
trap - EXIT HUP INT TERM
