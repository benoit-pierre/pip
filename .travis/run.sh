#!/bin/bash
set -e
set -x

if [[ $TOXENV == py* ]]; then
    if [[ $TOXENV == pypy* ]]; then
      jobs=6
    else
      jobs=8
    fi
    # Run unit tests
    tox -- -m unit
    # Run integration tests
    tox -- -m integration -n $jobs --duration=5
else
    # Run once
    tox
fi
