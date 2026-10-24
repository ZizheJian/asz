#!/bin/bash
#SBATCH --account=cis240669
#SBATCH --time=00:05:00
#SBATCH --cpus-per-task=1
#SBATCH --job-name=asz-rd-finalize
#SBATCH --output=results/final18-rd-finalize-%j.log

set -euo pipefail
cd /home/x-zjian1/asz
python_executable=/anvil/projects/x-cis240192/x-zjian1-in-cis240192/hdf_env/bin/python
"$python_executable" analyze_final_evaluation.py
"$python_executable" plot_final_rd.py
"$python_executable" plot_final_runtime.py
