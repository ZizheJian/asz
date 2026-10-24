#!/bin/bash
#SBATCH --account=cis240669
#SBATCH --time=00:20:00
#SBATCH --cpus-per-task=4
#SBATCH --array=0-5
#SBATCH --job-name=asz-precip-transfer
#SBATCH --output=results/isabel-precip-transfer-%A_%a.log

set -euo pipefail
cd /home/x-zjian1/asz
budgets=(1 2 4 8 16 48)
index=${SLURM_ARRAY_TASK_ID:?PRECIP transfer requires a Slurm array}
budget=${budgets[$index]}
python3 t1_start_compressors.py "configs/.isabel_precip_k${budget}.json" --skip-build --no-csv
