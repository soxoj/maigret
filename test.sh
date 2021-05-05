#!/bin/sh
coverage run --source=./maigret -m pytest tests
coverage report -m
coverage html
