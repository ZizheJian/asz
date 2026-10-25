#!/bin/bash
#SBATCH --account=cis240669
#SBATCH --time=00:20:00
#SBATCH --cpus-per-task=2
#SBATCH --array=0-5
#SBATCH --job-name=asz-dimensionality
#SBATCH --output=results/predictor-dimensionality-common-final18-20261024/slurm-%A_%a.log

set -euo pipefail
cd /home/x-zjian1/asz
output=results/predictor-dimensionality-common-final18-20261024
mkdir -p "$output"
case "$SLURM_ARRAY_TASK_ID" in
0) key=precip24;family=1d4r;data=/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/ISABEL/PRECIP/PRECIPf24.bin;shape=(100 500 500);;
1) key=precip24;family=2d4r;data=/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/ISABEL/PRECIP/PRECIPf24.bin;shape=(100 500 500);;
2) key=qmcpack144;family=1d4r;data=/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/QMCPACK/asz_qmcpack_orbital144.f32;shape=(115 69 69);;
3) key=qmcpack144;family=2d4r;data=/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/QMCPACK/asz_qmcpack_orbital144.f32;shape=(115 69 69);;
4) key=aramco1800;family=1d4r;data=/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/aramco/aramco-snapshot-1800.f32;shape=(449 449 235);;
5) key=aramco1800;family=2d4r;data=/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/aramco/aramco-snapshot-1800.f32;shape=(449 449 235);;
*) echo "unknown array index: $SLURM_ARRAY_TASK_ID" >&2;exit 2;;
esac
prefix="$output/$key"
bounds=0.1,0.01,0.001,0.0001,0.00001
binary=build/predictor_dimensionality/s2_many_prediction
if [[ ! -x "$binary" ]]||! "$binary" --help | grep -q 'common';then
    echo "missing common-target predictor diagnostic binary: $binary" >&2
    exit 2
fi
echo "dataset=$key family=$family data=$data shape=${shape[*]} bounds=$bounds"
"$binary" "$data" "${shape[0]}" "${shape[1]}" "${shape[2]}" "$prefix" "$family" "$bounds" legacy common
