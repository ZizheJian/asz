#!/bin/bash
#SBATCH --job-name=asz-family-mse-18a
#SBATCH --account=cis240669
#SBATCH --partition=shared
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=64
#SBATCH --mem=128G
#SBATCH --time=02:30:00
#SBATCH --output=results/slurm-%x-%j.out
#SBATCH --error=results/slurm-%x-%j.err

set -euo pipefail
cd /home/x-zjian1/asz
result_name="family-mse-eighteen-missing-${SLURM_JOB_ID}"
scratch_result="/anvil/scratch/x-zjian1/${result_name}"
python3 run_family_mse_validation.py --manifest configs/family_mse_validation_eighteen_missing.json --output "$scratch_result"
cp -a "$scratch_result" "results/$result_name"
