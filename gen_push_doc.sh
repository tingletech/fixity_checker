#!/usr/bin/env bash
set -eu
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd ) # http://stackoverflow.com/questions/59895
cd "$DIR"
docco fixity_checker.py
mv docs/fixity_checker.html docs/index.html
git subtree push --prefix docs origin gh-pages
