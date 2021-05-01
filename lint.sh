#!/bin/sh
FILES="maigret wizard.py maigret.py tests"

echo 'syntax errors or undefined names'
flake8 --count --select=E9,F63,F7,F82 --show-source --statistics $FILES

echo 'warning'
flake8 --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics --ignore=E731,W503 $FILES

echo 'mypy'
mypy ./maigret ./wizard.py ./tests