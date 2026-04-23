#!/bin/bash
set -e

sudo apt-get update && sudo apt-get install -y libcairo2-dev pkg-config
pip install .
