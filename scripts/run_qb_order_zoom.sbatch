#!/bin/bash
#SBATCH --account=cis240669
#SBATCH --time=00:10:00
#SBATCH --cpus-per-task=2
#SBATCH --array=0-2
#SBATCH --job-name=asz-qbo-zoom
#SBATCH --output=results/qb-order-zoom-final18-20261025/slurm-%A_%a.log

set -euo pipefail
cd /home/x-zjian1/asz
output=results/qb-order-zoom-final18-20261025
mkdir -p "$output"
case "$SLURM_ARRAY_TASK_ID" in
0) key=precip24;data=/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/ISABEL/PRECIP/PRECIPf24.bin;shape=(100 500 500);;
1) key=qmcpack144;data=/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/QMCPACK/asz_qmcpack_orbital144.f32;shape=(115 69 69);;
2) key=aramco1800;data=/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/aramco/aramco-snapshot-1800.f32;shape=(449 449 235);;
*) echo "unknown array index: $SLURM_ARRAY_TASK_ID" >&2;exit 2;;
esac
bounds=0.002,0.0015,0.001,0.00075,0.0005
binary=build/predictor_dimensionality/s2_many_prediction
if [[ ! -x "$binary" ]]||! "$binary" --help | grep -q 'common';then
    echo "missing common-target predictor diagnostic binary: $binary" >&2
    exit 2
fi
echo "dataset=$key data=$data shape=${shape[*]} bounds=$bounds"
"$binary" "$data" "${shape[0]}" "${shape[1]}" "${shape[2]}" "$output/$key" 1d4r "$bounds" legacy common
