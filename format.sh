#!/bin/sh
FILES="maigret wizard.py maigret.py"

echo 'black'
black --skip-string-normalization $FILES