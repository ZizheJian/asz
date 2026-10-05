#!/bin/bash
#SBATCH --job-name=asz-apsu006
#SBATCH --account=cis240669
#SBATCH --partition=shared
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=128
#SBATCH --time=06:00:00
#SBATCH --output=results/slurm-%x-%j.out
#SBATCH --error=results/slurm-%x-%j.err

set -euo pipefail

cd /home/x-zjian1/asz
source_path="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/APS_DYS/xpcs_datasets/APSU_TestData_006/APSU_TestData_006.h5"
data_path="${source_path}.f32"
hdf_python="/anvil/projects/x-cis240192/x-zjian1-in-cis240192/hdf_env/bin/python"
"${hdf_python}" convert_hdf5_to_f32.py "${source_path}" "${data_path}" --dataset /entry/data/data --shape 4096,1558,1813 --chunk-size 8

run_root="/tmp/asz-apsu006-${SLURM_JOB_ID}"
cmake -S c_codes -B "${run_root}/build" -DCODE_NAME=s1_compress -DCMAKE_BUILD_TYPE=Release
cmake --build "${run_root}/build" --target s1_compress s1_decompress --parallel 8
export ASZ_EXECUTABLE_DIRECTORY="${run_root}/build"
python3 t1_start_compressors.py apsu006 --skip-build --no-csv
