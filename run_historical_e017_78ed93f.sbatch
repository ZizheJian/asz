#!/bin/bash
#SBATCH --job-name=asz-hist-e017
#SBATCH --account=cis240669
#SBATCH --partition=shared
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=128G
#SBATCH --time=00:30:00
#SBATCH --output=results/slurm-%x-%j.out
#SBATCH --error=results/slurm-%x-%j.err

set -euo pipefail

project_root=/home/x-zjian1/asz
run_root=/tmp/asz-hist-e017-${SLURM_JOB_ID}
mkdir -p "${run_root}"
cd "${project_root}"
git archive 78ed93f c_codes | tar -xf - -C "${run_root}"
git -C third_party/zstd archive 48c0ed73625272cb7445183b5e256b5d0a130316 | tar -xf - -C "${run_root}/c_codes/third_party/zstd"
cp historical_reproduction/e017_78ed93f.cpp "${run_root}/c_codes/e017_78ed93f.cpp"
cmake -S "${run_root}/c_codes" -B "${run_root}/build" -DCODE_NAME=e017_78ed93f -DCMAKE_BUILD_TYPE=Release
cmake --build "${run_root}/build" --target e017_78ed93f --parallel "${SLURM_CPUS_PER_TASK}"
"${run_root}/build/e017_78ed93f" 0.001
