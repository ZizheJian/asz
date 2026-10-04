#!/bin/bash
#SBATCH --job-name=asz-refresh-merge
#SBATCH --account=cis240669
#SBATCH --partition=shared
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --time=00:10:00
#SBATCH --output=results/slurm-%x-%j.out
#SBATCH --error=results/slurm-%x-%j.err

set -euo pipefail

cd /home/x-zjian1/asz
python3 merge_final_eight_asz_refresh.py
python3 analyze_final_eight.py --file-prefix final_eight_frozen_ --output results/final_eight_frozen_comparison.csv
