#!/bin/bash
#SBATCH --job-name=asz-rtm-middle
#SBATCH --account=cis240669
#SBATCH --partition=shared
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --time=00:30:00
#SBATCH --output=results/slurm-%x-%j.out
#SBATCH --error=results/slurm-%x-%j.err

set -euo pipefail
cd /home/x-zjian1/asz
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export PYTHONUNBUFFERED=1
scratch_data=/anvil/scratch/x-zjian1/asz-rtm-middle-data
mkdir -p "$scratch_data"
if [ ! -e "$scratch_data/rtm-small-0360.f32" ]; then
    ln -s /anvil/projects/x-cis240669/RTM/RtmLab-smalldata-449x449x235/data-3600-intervals5/aramco-snapshot-0360.f32 "$scratch_data/rtm-small-0360.f32"
fi
if [ ! -e "$scratch_data/rtm-big-0750.f32" ]; then
    ln -s /anvil/projects/x-cis240669/RTM/RtmLab-bigdata-849x849x235/data-every10/aramco-snapshot-0750.f32 "$scratch_data/rtm-big-0750.f32"
fi
python3 t1_start_compressors.py configs/rtm_middle.json --skip-build --no-csv
