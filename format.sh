#!/bin/sh
FILES="maigret wizard.py maigret.py tests"

echo 'black'
black --skip-string-normalization $FILES