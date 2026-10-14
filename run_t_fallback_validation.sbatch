#!/bin/bash
#SBATCH --job-name=asz-t-fallback
#SBATCH --account=cis240669
#SBATCH --partition=shared
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=00:05:00
#SBATCH --array=0-12%2
#SBATCH --output=results/slurm-%x-%A_%a.out
#SBATCH --error=results/slurm-%x-%A_%a.err

set -euo pipefail
cd /home/x-zjian1/asz
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export PYTHONUNBUFFERED=1
: "${FALLBACK_OUTPUT:?FALLBACK_OUTPUT is required}"
python3 run_t_fallback_validation.py --task-index "$SLURM_ARRAY_TASK_ID" --output "$FALLBACK_OUTPUT"
