#!/bin/bash
#SBATCH --account=cis240669
#SBATCH --time=00:50:00
#SBATCH --cpus-per-task=4
#SBATCH --array=0-5
#SBATCH --job-name=asz-dimensionality
#SBATCH --output=results/predictor-dimensionality-final18-20261023/slurm-%A_%a.log

set -euo pipefail
cd /home/x-zjian1/asz
output=results/predictor-dimensionality-final18-20261023
mkdir -p "$output"
case "$SLURM_ARRAY_TASK_ID" in
0) key=precip24;family=1d4r;data=/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/ISABEL/PRECIP/PRECIPf24.bin;shape=(100 500 500);;
1) key=precip24;family=2d4r;data=/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/ISABEL/PRECIP/PRECIPf24.bin;shape=(100 500 500);;
2) key=vd01_31;family=1d4r;data=/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/cesm-atm-1.5TB/31/VD01_26x1800x3600.dat;shape=(26 1800 3600);;
3) key=vd01_31;family=2d4r;data=/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/cesm-atm-1.5TB/31/VD01_26x1800x3600.dat;shape=(26 1800 3600);;
4) key=aramco1800;family=1d4r;data=/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/aramco/aramco-snapshot-1800.f32;shape=(449 449 235);;
5) key=aramco1800;family=2d4r;data=/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/aramco/aramco-snapshot-1800.f32;shape=(449 449 235);;
*) echo "unknown array index: $SLURM_ARRAY_TASK_ID" >&2;exit 2;;
esac
prefix="$output/$key"
bounds=0.1,0.01,0.001,0.0001,0.00001
binary=build/predictor_dimensionality/s2_many_prediction
echo "dataset=$key family=$family data=$data shape=${shape[*]} bounds=$bounds"
"$binary" "$data" "${shape[0]}" "${shape[1]}" "${shape[2]}" "$prefix" "$family" "$bounds" legacy legacy
