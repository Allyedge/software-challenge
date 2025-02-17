#!/bin/sh

set -e

export XDG_CACHE_HOME=./.pip_cache

export PYTHONPATH=./packages:$PYTHONPATH

pip install --no-index --find-links=./dependencies/ ./dependencies/socha-1.0.8-py3-none-any.whl ./dependencies/xsdata-22.7-py3-none-any.whl --target=./packages/ --cache-dir=./.pip_cache

python3 ./main.py "$@"