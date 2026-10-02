#!/bin/bash
#SBATCH --job-name=asz-aps-huff
#SBATCH --account=cis240669
#SBATCH --partition=shared
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=00:15:00
#SBATCH --output=results/slurm-%x-%j.out
#SBATCH --error=results/slurm-%x-%j.err

set -euo pipefail

cd /home/x-zjian1/asz
run_root="/tmp/asz-aps-huff-${SLURM_JOB_ID}"
mkdir -p "${run_root}/control-src/third_party" "${run_root}/new-src/third_party" "${run_root}/head-huffman"
cp -a c_codes "${run_root}/control-src/"
cp -a c_codes "${run_root}/new-src/"
cp -a third_party/zstd "${run_root}/control-src/third_party/"
cp -a third_party/csv_tools "${run_root}/control-src/third_party/"
cp -a third_party/zstd "${run_root}/new-src/third_party/"
cp -a third_party/csv_tools "${run_root}/new-src/third_party/"
git archive HEAD c_codes/asz_core/huffman.hpp | tar -x -C "${run_root}/head-huffman"
cp "${run_root}/head-huffman/c_codes/asz_core/huffman.hpp" "${run_root}/control-src/c_codes/asz_core/huffman.hpp"
cmake -S "${run_root}/control-src/c_codes" -B "${run_root}/control-build" -DCODE_NAME=s1_compress -DCMAKE_BUILD_TYPE=Release
cmake --build "${run_root}/control-build" --target s1_decompress --parallel "${SLURM_CPUS_PER_TASK}"
cmake -S "${run_root}/new-src/c_codes" -B "${run_root}/new-build" -DCODE_NAME=s1_compress -DCMAKE_BUILD_TYPE=Release
cmake --build "${run_root}/new-build" --target s1_compress s1_decompress --parallel "${SLURM_CPUS_PER_TASK}"
python3 benchmark_decompression.py --old-asz-directory "${run_root}/control-build" --new-asz-directory "${run_root}/new-build" --work-directory "${run_root}/streams" --output "results/decompression_aps_huffman_${SLURM_JOB_ID}.csv" --repeat 5 --dataset APS_Kaz
