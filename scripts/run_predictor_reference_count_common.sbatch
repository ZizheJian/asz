#!/bin/bash
#SBATCH --account=cis240669
#SBATCH --time=00:40:00
#SBATCH --cpus-per-task=2
#SBATCH --array=0-35
#SBATCH --job-name=asz-reference-count
#SBATCH --output=results/predictor-reference-count-common-final18-20261025/slurm-%A_%a.log

set -euo pipefail
cd /home/x-zjian1/asz
output=results/predictor-reference-count-common-final18-20261025
mkdir -p "$output"
case "$SLURM_ARRAY_TASK_ID" in
0|1|2|3|4|5) key=precip24;offset=0;data=/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/ISABEL/PRECIP/PRECIPf24.bin;shape=(100 500 500);;
6|7|8|9|10|11) key=qmcpack144;offset=6;data=/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/QMCPACK/asz_qmcpack_orbital144.f32;shape=(115 69 69);;
12|13|14|15|16|17) key=aramco1800;offset=12;data=/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/aramco/aramco-snapshot-1800.f32;shape=(449 449 235);;
18|19|20|21|22|23) key=vd01_31;offset=18;data=/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/cesm-atm-1.5TB/31/VD01_26x1800x3600.dat;shape=(26 1800 3600);;
24|25|26|27|28|29) key=letkf_pres;offset=24;data=/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/SCALE_LETKF/PRES-98x1200x1200.dat;shape=(98 1200 1200);;
30|31|32|33|34|35) key=letkf_t;offset=30;data=/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/SCALE_LETKF/T-98x1200x1200.dat;shape=(98 1200 1200);;
*) echo "unknown array index: $SLURM_ARRAY_TASK_ID" >&2;exit 2;;
esac
slot=$((SLURM_ARRAY_TASK_ID-offset))
if ((slot<3));then family=1d4r;axis=$slot;else family=1d6r;axis=$((slot-3));fi
stencil=$family$axis
prefix="$output/$key"
bounds=0.1,0.01,0.001,0.0001,0.00001
binary=build/predictor_dimensionality/s2_many_prediction
if [[ ! -x "$binary" ]]||! "$binary" --help | grep -q 'family-or-stencil';then
    echo "missing exact-stencil predictor diagnostic binary: $binary" >&2
    exit 2
fi
echo "dataset=$key stencil=$stencil data=$data shape=${shape[*]} bounds=$bounds grid=transition targets=common"
"$binary" "$data" "${shape[0]}" "${shape[1]}" "${shape[2]}" "$prefix" "$stencil" "$bounds" transition common
