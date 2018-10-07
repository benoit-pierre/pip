#!/bin/bash
set -e

# Short circuit tests and linting jobs if there are no code changes involved.
if [[ $TOXENV != docs ]]; then
    if [[ "$TRAVIS_PULL_REQUEST" == "false" ]]
    then
        echo "This is not a PR -- will do a complete build."
    else
        # Pull requests are slightly complicated because $TRAVIS_COMMIT_RANGE
        # may include more changes than desired if the history is convoluted.
        # Instead, explicitly fetch the base branch and compare against the
        # merge-base commit.
        git fetch -q origin +refs/heads/$TRAVIS_BRANCH
        changes=$(git diff --name-only HEAD $(git merge-base HEAD FETCH_HEAD))
        echo "Files changed:"
        echo "$changes"
        if ! echo "$changes" | grep -qvE '(\.rst$)|(^docs)|(^news)|(^\.github)'
        then
            echo "Only Documentation was updated -- skipping build."
            exit
        fi
    fi
fi

# Export the correct TOXENV when not provided.
echo "Determining correct TOXENV..."
if [[ -z "$TOXENV" ]]; then
  export TOXENV='py'
fi
echo "TOXENV=${TOXENV}"

# Print the commands run for this test.
echo "cores: $(cat /proc/cpuinfo | grep '^processor' | wc -l)"
tox=(tox --)
case "${TRAVIS_PYTHON_VERSION}" in
  *pypy3*|3*)
    tox+=(--use-venv)
    ;;
esac
if [[ "$GROUP" == "1" ]]; then
  set -x
  # Unit tests
  "${tox[@]}" -m unit
  # Integration tests (not the ones for 'pip install')
  "${tox[@]}" -m integration -n 3 --duration=10 -k "not test_install"
elif [[ "$GROUP" == "2" ]]; then
  set -x
  # Separate Job for running integration tests for 'pip install'
  "${tox[@]}" -m integration -n 3 --duration=10 -k "test_install"
else
  set -x
  # Non-Testing Jobs should run once
  "${tox[@]}"
fi
