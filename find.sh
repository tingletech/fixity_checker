#!/usr/bin/env bash

set -eu
set -o pipefail

path=$1
shift

find "$path" -type f -exec python ~/code/fixity/checkfile.py {} "$@" \;
