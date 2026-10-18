#!/bin/bash
#SBATCH --account=cis240669
#SBATCH --partition=shared
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --output=results/slurm-%x-%j.out
#SBATCH --error=results/slurm-%x-%j.err

set -euo pipefail
cd /home/x-zjian1/asz
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export PYTHONUNBUFFERED=1
: "${SCREEN_CONFIG:?SCREEN_CONFIG is required}"
python3 t1_start_compressors.py "$SCREEN_CONFIG" --skip-build --no-csv
