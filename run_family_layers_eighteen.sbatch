#!/bin/bash
#SBATCH --job-name=asz-family-layers-18
#SBATCH --account=cis240669
#SBATCH --partition=shared
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=64G
#SBATCH --time=02:00:00
#SBATCH --output=results/slurm-%x-%j.out
#SBATCH --error=results/slurm-%x-%j.err

set -euo pipefail
cd /home/x-zjian1/asz
ground_truth="results/family-mse-eighteen-20261011"
mkdir "$ground_truth"
cp results/family-mse-six-21285600/*-controls.json "$ground_truth/"
cp results/family-mse-eighteen-missing-21296176/*-controls.json "$ground_truth/"
cp results/family-mse-apsu006-highmem-21299737/*-controls.json "$ground_truth/"
python3 analyze_family_mse.py --input results/family-mse-six-21285600/raw.csv results/family-mse-eighteen-missing-21296176/raw.csv results/family-mse-apsu006-highmem-21299737/raw.csv --output "$ground_truth/analysis"
python3 run_predictor_family_block_validation.py --manifest configs/family_mse_validation_eighteen.json --controls "$ground_truth" --ground-truth "$ground_truth/analysis/cases.csv" --output results/family-block-four-eighteen-20261011 --suffix-layers 4 --sample-blocks 16 --seed-mode pivot
python3 run_predictor_family_block_validation.py --manifest configs/family_mse_validation_eighteen.json --controls "$ground_truth" --ground-truth "$ground_truth/analysis/cases.csv" --output results/family-block-six-eighteen-20261011 --suffix-layers 6 --sample-blocks 16 --seed-mode pivot
python3 run_predictor_family_block_validation.py --manifest configs/family_mse_validation_eighteen.json --controls "$ground_truth" --ground-truth "$ground_truth/analysis/cases.csv" --output results/family-block-eight-eighteen-20261011 --suffix-layers 8 --sample-blocks 16 --seed-mode pivot
