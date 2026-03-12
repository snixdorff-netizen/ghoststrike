#!/bin/sh
set -eu

python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'

export ADA_IQ_DB_PATH="${ADA_IQ_DB_PATH:-data/ada_iq.db}"
export ADA_IQ_SEED_PATH="${ADA_IQ_SEED_PATH:-src/ada_iq/data/demo_projects.json}"
export ADA_IQ_AUTO_SEED="${ADA_IQ_AUTO_SEED:-true}"

exec python3 -m ada_iq.worker
