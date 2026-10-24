#!/bin/bash
#SBATCH --account=cis240669
#SBATCH --output=results/final18-rd-%j.log

set -euo pipefail
cd /home/x-zjian1/asz
group=${1:?缺少实验组名称}
if [[ "$group" == "apsu006" || "$group" == "apsu006_sperr" ]];then
    index=${SLURM_ARRAY_TASK_ID:?APSU006需要Slurm array}
    configuration="configs/.final18_rd_${group}_${index}.json"
else
    configuration="configs/.final18_rd_${group}.json"
fi
export ASZ_EXECUTABLE_DIRECTORY=/home/x-zjian1/asz/build/final18_rd_bin
python3 t1_start_compressors.py "$configuration" --skip-build --no-csv
