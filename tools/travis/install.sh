#!/bin/bash
set -e
set -x

pip install --upgrade pip --disable-pip-version-check
pip install --upgrade setuptools wheel
pip install --upgrade tox
pip freeze --all
