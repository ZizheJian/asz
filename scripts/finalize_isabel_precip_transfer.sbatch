#!/bin/bash
#SBATCH --account=cis240669
#SBATCH --time=00:05:00
#SBATCH --cpus-per-task=1
#SBATCH --job-name=asz-precip-finalize
#SBATCH --output=results/isabel-precip-finalize-%j.log

set -euo pipefail
cd /home/x-zjian1/asz
python3 scripts/prepare_isabel_precip_transfer.py --finalize
