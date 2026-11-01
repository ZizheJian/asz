#!/bin/bash
#SBATCH --account=cis240669
#SBATCH --job-name=asz-temporal-reuse
#SBATCH --output=results/temporal-plan-reuse-%j.log

set -euo pipefail
cd /home/x-zjian1/asz
field=${1:?缺少field名称}
parallel=${2:-${SLURM_CPUS_PER_TASK:-1}}
export ASZ_EXECUTABLE_DIRECTORY=/home/x-zjian1/asz/build/final18_rd_bin
for phase in self transfer;do
    python3 scripts/prepare_temporal_plan_reuse.py --field "$field" --pending "$phase"|xargs -r -n 1 -P "$parallel" python3 t1_start_compressors.py --skip-build --no-csv
done
python3 analyze_temporal_plan_reuse.py --field "$field"
