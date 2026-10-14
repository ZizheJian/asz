#!/bin/bash
#SBATCH --job-name=asz-family-006-debug-a
#SBATCH --account=cis240669
#SBATCH --partition=debug
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=160G
#SBATCH --time=02:00:00
#SBATCH --output=results/slurm-%x-%j.out
#SBATCH --error=results/slurm-%x-%j.err

set -euo pipefail
cd /home/x-zjian1/asz
input_copy="/anvil/scratch/x-zjian1/family-mse-apsu006-debug-input.f32"
result_name="family-mse-apsu006-debug-a-${SLURM_JOB_ID}"
scratch_result="/anvil/scratch/x-zjian1/${result_name}"
cp /anvil/projects/x-cis240192/x-zjian1-in-cis240192/tensor-data/APS_DYS/xpcs_datasets/APSU_TestData_006/APSU_TestData_006.h5.f32 "$input_copy"
python3 run_family_mse_validation.py --manifest configs/family_mse_validation_apsu006_debug_a.json --output "$scratch_result"
cp -a "$scratch_result" "results/$result_name"
