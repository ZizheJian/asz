#!/bin/bash
#SBATCH --job-name=asz-validate-results
#SBATCH --account=cis240669
#SBATCH --partition=shared
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --time=00:05:00
#SBATCH --output=results/slurm-%x-%j.out
#SBATCH --error=results/slurm-%x-%j.err

set -euo pipefail
cd /home/x-zjian1/asz
: "${FALLBACK_OUTPUT:?FALLBACK_OUTPUT is required}"
python3 analyze_t_fallback_validation.py "$FALLBACK_OUTPUT"
python3 validate_fallback_rtm_results.py --fallback "$FALLBACK_OUTPUT" --output "$FALLBACK_OUTPUT/validation.json"
