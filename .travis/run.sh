#!/bin/bash
set -e
set -x

if [[ $TOXENV == py* ]]; then
    # Run unit tests
    tox -- -m unit -n 3
    # Run integration tests
    tox -- -m 'integration and not slow' -n 3 --duration=5
    tox -- -m 'integration and slow' -n 3 --duration=5
else
    # Run once
    tox
fi
