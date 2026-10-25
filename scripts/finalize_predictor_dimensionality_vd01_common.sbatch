#!/bin/bash
#SBATCH --account=cis240669
#SBATCH --time=00:01:00
#SBATCH --cpus-per-task=1
#SBATCH --job-name=asz-vd01-finalize
#SBATCH --output=results/predictor-dimensionality-common-vd01-20261024/slurm-%j.log

set -euo pipefail
cd /home/x-zjian1/asz
output=results/predictor-dimensionality-common-vd01-20261024
python3 summarize_prediction_sweep.py "$output/vd01_31" --family 1d4r 2d4r --retain axis --selection shared-slope --target-bound 0.1 0.01 0.001 0.0001 0.00001 --require-uniform-samples --output "$output/vd01_31-best.csv"
