#!/bin/bash
#SBATCH --account=cis240669
#SBATCH --time=00:21:00
#SBATCH --cpus-per-task=2
#SBATCH --array=0-1
#SBATCH --job-name=asz-vd01-common
#SBATCH --output=results/predictor-dimensionality-common-vd01-20261024/slurm-%A_%a.log

set -euo pipefail
cd /home/x-zjian1/asz
output=results/predictor-dimensionality-common-vd01-20261024
mkdir -p "$output"
case "$SLURM_ARRAY_TASK_ID" in
0) family=1d4r;;
1) family=2d4r;;
*) echo "unknown array index: $SLURM_ARRAY_TASK_ID" >&2;exit 2;;
esac
data=/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/cesm-atm-1.5TB/31/VD01_26x1800x3600.dat
shape=(26 1800 3600)
bounds=0.1,0.01,0.001,0.0001,0.00001
binary=build/predictor_dimensionality/s2_many_prediction
if [[ ! -x "$binary" ]]||! "$binary" --help | grep -q 'common';then
    echo "missing common-target predictor diagnostic binary: $binary" >&2
    exit 2
fi
echo "dataset=vd01_31 family=$family data=$data shape=${shape[*]} bounds=$bounds"
"$binary" "$data" "${shape[0]}" "${shape[1]}" "${shape[2]}" "$output/vd01_31" "$family" "$bounds" legacy common
