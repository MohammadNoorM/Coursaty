#!/usr/bin/env bash
set -o errexit
pip install -r requirements.txt
python scripts/build_css.py
python manage.py collectstatic --no-input
python manage.py migrate
