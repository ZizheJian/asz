#!/bin/bash
#SBATCH --account=cis240669
#SBATCH --time=00:02:00
#SBATCH --cpus-per-task=1
#SBATCH --job-name=asz-reference-finalize
#SBATCH --output=results/predictor-reference-count-common-final18-20261025/slurm-%j.log

set -euo pipefail
cd /home/x-zjian1/asz
output=results/predictor-reference-count-common-final18-20261025
targets=(0.1 0.01 0.001 0.0001 0.00001)
for key in precip24 vd01_31 letkf_t aramco1800 letkf_pres qmcpack144;do
    python3 summarize_prediction_sweep.py "$output/$key" --family 1d4r 1d6r --retain axis --selection shared-slope --target-bound "${targets[@]}" --require-uniform-samples --output "$output/$key-best.csv"
done
for key in aramco1800 letkf_pres qmcpack144;do
    python3 summarize_prediction_sweep.py "$output/$key" --family 1d6r --retain coefficient --selection shared-slope --target-bound "${targets[@]}" --require-uniform-samples --output "$output/$key-1d6r-coefficients.csv"
done
