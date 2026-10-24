#!/bin/bash
#SBATCH --account=cis240669
#SBATCH --time=00:20:00
#SBATCH --cpus-per-task=4
#SBATCH --job-name=asz-precip-self
#SBATCH --output=results/isabel-precip-self-%j.log

set -euo pipefail
cd /home/x-zjian1/asz
python3 t1_start_compressors.py configs/.isabel_precip_self.json --skip-build --no-csv
