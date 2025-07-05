#!/bin/bash
if [ -z "$1" ]; then
  echo "Usage: $0 \"your migration message\""
  exit 1
fi
# Ensure alembic refers to the correct alembic.ini
# This assumes the script is run from the project root or alembic can find its ini
# Or, explicitly pass -c alembic.ini if needed, but usually alembic handles this if run from root.
alembic revision -m "$1" --autogenerate
