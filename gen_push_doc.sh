#!/usr/bin/env bash
set -eu
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd ) # http://stackoverflow.com/questions/59895
cd "$DIR"
docco fixity_checker.py
git subtree push --prefix docs origin gh-pages
