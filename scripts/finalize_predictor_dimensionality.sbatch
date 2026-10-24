#!/bin/bash
#SBATCH --account=cis240669
#SBATCH --time=00:05:00
#SBATCH --cpus-per-task=1
#SBATCH --job-name=asz-dimensionality-finalize
#SBATCH --output=results/predictor-dimensionality-final18-20261023/slurm-%j.log

set -euo pipefail
cd /home/x-zjian1/asz
output=results/predictor-dimensionality-final18-20261023
targets=(0.1 0.01 0.001 0.0001 0.00001)
for key in precip24 vd01_31 aramco1800;do
    python3 summarize_prediction_sweep.py "$output/$key" --family 1d4r 2d4r --retain axis --selection shared-slope --target-bound "${targets[@]}" --output "$output/$key-best.csv"
done
