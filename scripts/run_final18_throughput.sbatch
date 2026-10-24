#!/bin/bash
#SBATCH --account=cis240669
#SBATCH --output=results/final18-throughput-%j.log

set -euo pipefail
cd /home/x-zjian1/asz
group=${1:?缺少实验组名称}
configuration="configs/.final18_throughput_${group}.json"
python3 t1_start_compressors.py "$configuration" --skip-build --no-csv
