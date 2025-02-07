#!/bin/bash
cd /home/kavia/workspace/API-Performance-Optimization-L.0.2/main_component

# 1.) Run the linters on the files or directories passed as arguments
black "$@"
BLACK_EXIT_CODE=$?

flake8 "$@"
FLAKE8_EXIT_CODE=$?

isort "$@"
ISORT_EXIT_CODE=$?

# 2.) Test the packaging of the application
pip install -e .
INSTALL_EXIT_CODE=$?

# Exit with error if any command failed
if [ $BLACK_EXIT_CODE -ne 0 ] || [ $FLAKE8_EXIT_CODE -ne 0 ] || [ $ISORT_EXIT_CODE -ne 0 ] || [ $INSTALL_EXIT_CODE -ne 0 ]; then
    exit 1
fi